module.exports = {
  apps: [
    {
      name: 'minihack-audit-api',
      script: 'app.py',
      interpreter: './venv/bin/python',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      env: {
        FLASK_ENV: 'development',
        PORT: 5005
      },
      env_production: {
        FLASK_ENV: 'production',
        PORT: 5005
      },
      error_file: 'logs/pm2-error.log',
      out_file: 'logs/pm2-out.log',
      merge_logs: true,
      time: true
    }
  ]
};
