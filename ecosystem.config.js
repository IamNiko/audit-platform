module.exports = {
  apps: [
    {
      name: 'minihack-audit-api',
      script: './venv/bin/gunicorn',
      args: '--workers 2 --threads 4 --timeout 120 --bind 127.0.0.1:5005 app:app',
      interpreter: 'none',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      env: {
        FLASK_ENV: 'production',
        FLASK_DEBUG: '0',
        PORT: 5005
      },
      env_production: {
        FLASK_ENV: 'production',
        FLASK_DEBUG: '0',
        PORT: 5005
      },
      error_file: 'logs/pm2-error.log',
      out_file: 'logs/pm2-out.log',
      merge_logs: true,
      time: true
    }
  ]
};
