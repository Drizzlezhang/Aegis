module.exports = {
  apps: [
    {
      name: 'aegis-trader-analyzer',
      script: 'python',
      args: '-m src.cli analyze --all',
      cwd: '/app',
      instances: 1,
      autorestart: false,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        AEGIS_ENVIRONMENT: 'production',
        AEGIS_LOG_LEVEL: 'INFO',
      },
      env_production: {
        NODE_ENV: 'production',
        AEGIS_ENVIRONMENT: 'production',
        AEGIS_LOG_LEVEL: 'INFO',
      },
      error_file: '/app/logs/analyzer-err.log',
      out_file: '/app/logs/analyzer-out.log',
      log_file: '/app/logs/analyzer-combined.log',
      time: true,
      // Run as a cron-like job (every day at 09:30 UTC, before US market open)
      cron_restart: '30 9 * * 1-5',
    },
    {
      name: 'aegis-trader-web',
      script: 'npm',
      args: 'start',
      cwd: '/app/web',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
        NEXT_PUBLIC_API_URL: 'http://localhost:8000',
      },
      env_production: {
        NODE_ENV: 'production',
        PORT: 3000,
        NEXT_PUBLIC_API_URL: 'http://localhost:8000',
      },
      error_file: '/app/logs/web-err.log',
      out_file: '/app/logs/web-out.log',
      log_file: '/app/logs/web-combined.log',
      time: true,
    },
  ],

  deploy: {
    production: {
      user: 'ubuntu',
      host: '18.136.151.164',
      ref: 'origin/master',
      repo: 'https://github.com/Drizzlezhang/Aegis-Trader.git',
      path: '/home/ubuntu/aegis-trader',
      'post-deploy': 'docker-compose -f docker-compose.yml up -d --build && pm2 reload ecosystem.config.js --env production',
      env: {
        NODE_ENV: 'production',
        AEGIS_ENVIRONMENT: 'production',
      },
    },
  },
};
