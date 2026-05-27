"""APScheduler-based daily analysis scheduler."""

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.agents.orchestrator import Orchestrator
from src.config import get_config
from src.observability.metrics import get_pipeline_metrics
from src.services.notification.telegram import TelegramNotifier
from src.services.tracking.service import TrackingService
from src.services.watchlist import WatchlistService

logger = logging.getLogger(__name__)


class AnalysisScheduler:
    """定时调度 Watchlist 全量分析。"""

    def __init__(self, orchestrator: Orchestrator):
        self._config = get_config().scheduler
        self._scheduler = AsyncIOScheduler(timezone=self._config.timezone)
        self._orchestrator = orchestrator
        self._watchlist = WatchlistService()
        self._notifier = TelegramNotifier()
        self._tracking = TrackingService()
        self._last_run: dict | None = None
        self._running = False

    async def initialize(self):
        """注册定时任务。"""
        hour, minute = map(int, self._config.daily_run_time.split(":"))
        trigger = CronTrigger(hour=hour, minute=minute, timezone=self._config.timezone)
        self._scheduler.add_job(self.run_daily_analysis, trigger, id="daily_analysis")
        logger.info(
            f"Scheduler configured: daily at {self._config.daily_run_time} {self._config.timezone}"
        )

        update_trigger = CronTrigger(hour=16, minute=30, timezone=self._config.timezone)
        self._scheduler.add_job(self._tracking.update_all, update_trigger, id="tracking_update")
        logger.info("Tracking update configured: daily at 16:30")

        # Daily tracking summary notification at 17:00 (after tracking update at 16:30)
        summary_trigger = CronTrigger(hour=17, minute=0, day_of_week="mon-fri",
                                      timezone=self._config.timezone)
        self._scheduler.add_job(
            self._send_daily_summary,
            summary_trigger,
            id="daily_tracking_summary",
        )
        logger.info("Daily tracking summary configured: weekdays at 17:00")

    def start(self):
        if self._config.enabled:
            self._scheduler.start()
            logger.info("Scheduler started")

    def stop(self):
        self._scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    async def aclose(self):
        """Async cleanup — close notifier client."""
        await self._notifier.close()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> dict:
        jobs = self._scheduler.get_jobs()
        return {
            "enabled": self._config.enabled,
            "running": self._running,
            "next_run": str(jobs[0].next_run_time) if jobs else None,
            "last_run": self._last_run,
        }

    async def run_daily_analysis(self):
        """执行每日全量分析。"""
        if self._running:
            logger.warning("Analysis already running, skipping")
            return

        self._running = True
        symbols = self._watchlist.get_symbols()

        if not symbols:
            logger.info("Watchlist is empty, nothing to analyze")
            self._running = False
            return

        logger.info(f"Starting daily analysis for {len(symbols)} symbols: {symbols}")

        semaphore = asyncio.Semaphore(self._config.max_concurrent_analyses)

        async def analyze_one(symbol: str) -> dict:
            async with semaphore:
                try:
                    state = await self._orchestrator.analyze_symbol(symbol)
                    recs = state.recommended_options
                    confidence = (
                        max((r.get("confidence", 0) for r in recs), default=0) if recs else 0
                    )
                    high_conf = confidence >= get_config().telegram.confidence_threshold

                    result = {
                        "symbol": symbol,
                        "success": True,
                        "recommendations": len(recs),
                        "high_confidence": high_conf,
                        "top_strategy": recs[0].get("strategy_type") if recs else None,
                        "trace_id": state.metadata.get("trace_id"),
                    }

                    if recs:
                        top = recs[0]
                        self._tracking.record_recommendation(
                            symbol=symbol,
                            strategy_type=top.get("strategy_type", "unknown"),
                            entry_price=top.get("entry_price", 0),
                            target_price=top.get("target_price"),
                            stop_loss=top.get("stop_loss"),
                            confidence=confidence,
                        )

                    if high_conf:
                        await self._notifier.notify_analysis_complete(symbol, recs, confidence)

                    return result
                except Exception as e:
                    logger.error(f"Analysis failed for {symbol}: {e}")
                    await self._notifier.notify_error(f"Daily analysis: {symbol}", str(e))
                    return {"symbol": symbol, "success": False, "error": str(e)}

        tasks = [analyze_one(s) for s in symbols]
        results = await asyncio.gather(*tasks)

        await self._notifier.notify_daily_summary(results)

        self._last_run = {
            "timestamp": datetime.now().isoformat(),
            "total": len(results),
            "success": sum(1 for r in results if r.get("success")),
            "results": results,
        }
        self._running = False
        logger.info(
            f"Daily analysis completed: {self._last_run['success']}/{self._last_run['total']} success"
        )

    async def run_single(self, symbol: str) -> dict:
        """手动触发单个标的分析。"""
        state = await self._orchestrator.analyze_symbol(symbol)
        return {
            "symbol": symbol,
            "recommendations": len(state.recommended_options),
            "trace_id": state.metadata.get("trace_id"),
        }

    def reschedule_job(self, job_id: str, **trigger_kwargs) -> None:
        """Reschedule a job by ID with new trigger kwargs."""
        try:
            trigger = CronTrigger(**trigger_kwargs, timezone=self._config.timezone)
            self._scheduler.reschedule_job(job_id, trigger=trigger)
            logger.info(f"Rescheduled job {job_id}")
        except Exception as e:
            logger.warning(f"Failed to reschedule job {job_id}: {e}")

    async def _send_daily_summary(self):
        """Send daily tracking summary via Telegram."""
        try:
            stats = self._tracking.get_stats()
            if stats.get("total", 0) == 0:
                return
            await self._notifier.send_tracking_summary(stats)
        except Exception as e:
            logger.error(f"Failed to send daily tracking summary: {e}")