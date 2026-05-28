"""APScheduler-based daily analysis scheduler."""

import asyncio
import logging
import time
from datetime import datetime

from apscheduler.events import EVENT_JOB_MISSED
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.agents.orchestrator import Orchestrator
from src.config import get_config
from src.scheduler.history import get_session, record_end, record_skipped, record_start
from src.services.notification.telegram import TelegramNotifier
from src.services.tracking.service import TrackingService
from src.services.watchlist import WatchlistService

logger = logging.getLogger(__name__)


def _build_jobstores() -> dict | None:
    """Build jobstore dict based on config. Returns None for default MemoryJobStore."""
    config = get_config().scheduler
    if not config.persistent_jobstore:
        return None
    try:
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        db_url = get_config().database.url
        jobstore = SQLAlchemyJobStore(url=db_url)
        logger.info("Using SQLAlchemyJobStore for scheduler persistence")
        return {"default": jobstore}
    except Exception as e:
        logger.warning(
            f"SQLAlchemyJobStore init failed, falling back to MemoryJobStore: {e}"
        )
        return None


class AnalysisScheduler:
    """定时调度 Watchlist 全量分析。"""

    def __init__(self, orchestrator: Orchestrator):
        self._config = get_config().scheduler
        self._orchestrator = orchestrator
        self._watchlist = WatchlistService()
        self._notifier = TelegramNotifier()
        self._tracking = TrackingService()
        self._last_run: dict | None = None
        self._running = False

        jobstores = _build_jobstores()
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone=self._config.timezone,
        )

    async def initialize(self):
        """注册定时任务。"""
        hour, minute = map(int, self._config.daily_run_time.split(":"))
        trigger = CronTrigger(hour=hour, minute=minute, timezone=self._config.timezone)
        self._scheduler.add_job(
            self.run_daily_analysis, trigger, id="daily_analysis",
            max_instances=1, replace_existing=True,
        )
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

        # Listen for missed jobs (concurrency skip) and record SKIPPED
        def _on_job_missed(event: object) -> None:
            if getattr(event, "job_id", None) == "daily_analysis":
                try:
                    session = get_session()
                    record_skipped(session, getattr(event, "job_id", ""))
                    session.close()
                except Exception as e:
                    logger.warning(f"Failed to record skipped job: {e}")

        self._scheduler.add_listener(_on_job_missed, EVENT_JOB_MISSED)

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
        start_time = time.monotonic()
        history_id: int | None = None
        error_msg: str | None = None

        # Record start in history
        try:
            session = get_session()
            history_id = record_start(session, "daily_analysis")
            session.close()
        except Exception as e:
            logger.warning(f"Failed to record history start: {e}")

        try:
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
            logger.info(
                f"Daily analysis completed: {self._last_run['success']}/{self._last_run['total']} success"
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Daily analysis failed: {e}")
        finally:
            self._running = False
            # Record end in history
            if history_id is not None:
                try:
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    status = "FAILED" if error_msg else "SUCCESS"
                    session = get_session()
                    record_end(session, history_id, status, duration_ms, error_msg)
                    session.close()
                except Exception as e:
                    logger.warning(f"Failed to record history end: {e}")

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

    def list_jobs(self) -> list[dict]:
        """List all registered jobs for CLI."""
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": j.id,
                "name": j.name,
                "next_run_time": str(j.next_run_time) if j.next_run_time else None,
                "trigger": str(j.trigger),
            }
            for j in jobs
        ]

    def pause_job(self, job_id: str) -> bool:
        """Pause a job by ID. Returns True if successful."""
        try:
            self._scheduler.pause_job(job_id)
            logger.info(f"Paused job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to pause job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job by ID. Returns True if successful."""
        try:
            self._scheduler.resume_job(job_id)
            logger.info(f"Resumed job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to resume job {job_id}: {e}")
            return False

    def trigger_job(self, job_id: str) -> bool:
        """Manually trigger a job by ID (fire-and-forget). Returns True if job found."""
        job = self._scheduler.get_job(job_id)
        if job is None:
            return False
        job.func = job.func  # no-op, just validate
        try:
            self._scheduler.modify_job(job_id, next_run_time=datetime.now())
            logger.info(f"Triggered job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to trigger job {job_id}: {e}")
            return False

    async def _send_daily_summary(self):
        """Send daily tracking summary via Telegram."""
        try:
            stats = self._tracking.get_stats()
            if stats.get("total", 0) == 0:
                return
            await self._notifier.send_tracking_summary(stats)
        except Exception as e:
            logger.error(f"Failed to send daily tracking summary: {e}")
