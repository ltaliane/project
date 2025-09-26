from flask import Flask, render_template
from flask import Flask, render_template, jsonify
import ftplib
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import quantstats_lumi as qs
import schedule
import time
import threading
from datetime import datetime
import os
import socket

app = Flask(__name__)

class AutomatedFTPUpdater:
    def __init__(self):
        self.ftp_config = {
            'host': '49.12.228.153',
            'port': 2962, 
            'user': 'pnl_Vanton',
            'passwd': '377.Y?t71^g,lG',
            'timeout': 30,
            'path': '/'
        }
        self.files = ['1548021_PnL.csv', '44243855_PnL.csv']
        self.last_update = None
        self.is_updating = False
        
    def test_connection(self):
        """Проверка подключения с улучшенной обработкой ошибок"""
        try:
            print(f"Попытка подключения к {self.ftp_config['host']}:{self.ftp_config['port']}")
            
            # Проверяем доступность порта
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((self.ftp_config['host'], self.ftp_config['port']))
            sock.close()
            
            if result == 0:
                print("Порт доступен")
            else:
                return False, f"Порт {self.ftp_config['port']} недоступен"
            
            # Пробуем подключиться к FTP с таймаутом
            ftp = ftplib.FTP()
            ftp.login(self.ftp_config['user'], self.ftp_config['passwd'])
            ftp.connect(self.ftp_config['host'], self.ftp_config['port'], timeout=self.ftp_config['timeout'])
            
            # Проверяем пассивный режим
            ftp.set_pasv(True)  # Включить пассивный режим (обычно решает проблемы с файрволом)
            
            print("FTP подключение успешно")
            ftp.quit()
            return True, "Подключение успешно"
            
        except socket.timeout:
            return False, f"Таймаут подключения к {self.ftp_config['host']}"
        except ftplib.all_errors as e:
            return False, f"Ошибка FTP: {str(e)}"
        except Exception as e:
            return False, f"Общая ошибка: {str(e)}"
        
    def download_files(self):
      try:
        # Попытка подключения
        ftp = ftplib.FTP()
        ftp.connect(self.ftp_config['host'], self.ftp_config['port'], timeout=self.ftp_config['timeout'])
        ftp.login(self.ftp_config['user'], self.ftp_config['passwd'])
          
            # Проверяем пассивный режим
        ftp.set_pasv(True)  # Включить пассивный режим (обычно решает проблемы с файрволом)
            
        print("FTP подключение успешно")

        for filename in self.files:
            with open(filename, 'wb') as f:
                ftp.retrbinary(f'RETR {filename}', f.write)
            print(f'Загружен: {filename}')

        ftp.quit()
        return True, "Файлы успешно обновлены"

      except socket.gaierror as e:
        return False, f"Ошибка разрешения имени хоста: {e}. Проверьте правильность имени хоста."
      except ftplib.all_errors as e:
        return False, f"Ошибка FTP: {e}"
      except Exception as e:
        print(e)
        return False, f"Общая ошибка: {e}"
    
    def generate_report(self):
      
        try:
          csv_file = '1548021_PnL.csv'
          df = pd.read_csv(csv_file, sep=",", encoding='utf-8')
          df.columns = [c.replace('*', '') for c in df.columns]
          df = df[df['date'].astype(str).str.match(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}")]
          df['date'] = df['date'].str.strip()
          df['date'] = pd.to_datetime(df['date'], format='%Y.%m.%d %H:%M')
          df = df.set_index('date')

          # Обрабатываем доходность
          returns = df['daily_return'] / 100

          # Генерация отчета
          qs.reports.html(returns, output='templates/1548021.html', title='P&L Quantstats Report')
          print('✅ Отчет 1548021 успешно сгенерирован')
          
        except Exception as e:
            print(f'❌ Ошибка при генерации отчета 1548021: {e}')
          
        try:
          csv_file = '44243855_PnL.csv'
          df = pd.read_csv(csv_file, sep=",", encoding='utf-8')
          df.columns = [c.replace('*', '') for c in df.columns]
          df = df[df['date'].astype(str).str.match(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}")]
          df['date'] = df['date'].str.strip()
          df['date'] = pd.to_datetime(df['date'], format='%Y.%m.%d %H:%M')
          df = df.set_index('date')

              # Обрабатываем доходность
          returns = df['daily_return'] / 100

              # Генерация отчета
          qs.reports.html(returns, output='templates/44243855.html', title='P&L Quantstats Report')
          return True, '✅ Отчет 44243855 успешно сгенерирован'
              
        except Exception as e:
          return False, f'❌ Ошибка при генерации отчета 44243855: {e}'
    
    def update_process(self):
        """Полный процесс обновления"""
        if self.is_updating:
            return False, "Обновление уже выполняется"
        
        self.is_updating = True
        try:
            # Загрузка файлов
            success, message = self.download_files()
            if not success:
                return success, message
            
            # Генерация отчета
            success, message = self.generate_report()
            if success:
                self.last_update = datetime.now()
            
            return success, message
        finally:
            self.is_updating = False
    
    def scheduled_update(self):
        """Запланированное обновление"""
        def job():
            success, message = self.update_process()
            print(f"[{datetime.now()}] Автообновление: {message}")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=job)
        thread.start()

# Инициализация
updater = AutomatedFTPUpdater()

# Настройка расписания (ежедневно в 9:00)
schedule.every().day.at("09:00").do(updater.scheduled_update)

def run_scheduler():
    """Запуск планировщика в отдельном потоке"""
    while True:
        schedule.run_pending()
        time.sleep(60)

# Запускаем планировщик
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True
scheduler_thread.start()

@app.route('/')
def index():
    """Главная страница с информацией о статусе"""
    status_info = {
        'last_update': updater.last_update.strftime("%Y-%m-%d %H:%M:%S") if updater.last_update else "Никогда",
        'is_updating': updater.is_updating
    }
    return render_template('index.html', status=status_info)

@app.route('/api/update', methods=['POST'])
def manual_update():
    """Ручное обновление через API"""
    def update_task():
        success, message = updater.update_process()
        # Здесь можно добавить уведомления и т.д.
    
    # Запускаем в отдельном потоке чтобы не блокировать Flask
    thread = threading.Thread(target=update_task)
    thread.start()
    
    return jsonify({
        'status': 'started', 
        'message': 'Процесс обновления запущен',
        'last_update': updater.last_update.strftime("%Y-%m-%d %H:%M:%S") if updater.last_update else None
    })

@app.route('/api/status')
def get_status():
    """Получение статуса обновления"""
    return jsonify({
        'last_update': updater.last_update.strftime("%Y-%m-%d %H:%M:%S") if updater.last_update else None,
        'is_updating': updater.is_updating
    })



@app.route('/1548021')
def schet():
  return render_template('1548021.html')

@app.route('/44243855')
def schet2():
  return render_template('44243855.html')

if __name__ == '__main__':
    # Первоначальное обновление при запуске
    print("Запуск первоначального обновления...")
    updater.scheduled_update()
    
    app.run(debug=True, host='0.0.0.0', port=5000)