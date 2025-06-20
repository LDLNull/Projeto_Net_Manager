import sys
import platform
import subprocess
import os
import tempfile
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
)


# Function to get the next instance name (now "Grupo A", "Grupo B", etc.)
def get_instance_name():
    temp_file = tempfile.gettempdir() + '/instance_count.txt'
    
    if not os.path.exists(temp_file):
        with open(temp_file, 'w') as f:
            f.write('0')
    
    with open(temp_file, 'r+') as f:
        count = int(f.read().strip())
        count += 1
        f.seek(0)
        f.write(str(count))
    
    return f"Grupo {chr(64 + count)}"  # Now returns "Grupo A", "Grupo B", etc.


class WorkerSignals(QObject):
    result = pyqtSignal(str, str)  # host, status


class PingWorker(QRunnable):
    def __init__(self, host):
        super().__init__()
        self.host = host.strip()
        self.signals = WorkerSignals()

    def run(self):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", self.host]

        try:
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=True,
            )
            status = "On"
        except subprocess.CalledProcessError:
            status = "Off"
        except subprocess.TimeoutExpired:
            status = "Off"
        except Exception:
            status = "Off"

        self.signals.result.emit(self.host, status)


class PingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(get_instance_name())  # Now sets "Grupo A", "Grupo B", etc.
        self.setMinimumSize(500, 400)
        self.threadpool = QThreadPool()

        # Create a temporary file for instance count
        self.temp_file_path = tempfile.gettempdir() + '/instance_count.txt'

        # Layouts
        self.layout = QVBoxLayout()
        self.input_layout = QHBoxLayout()

        # Input field for hosts
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Insira os endereços IP ou nomes de host separados por vírgulas")
        self.input_layout.addWidget(self.host_input)

        # Ping button
        self.ping_button = QPushButton("Ping")
        self.ping_button.clicked.connect(self.start_ping)
        self.input_layout.addWidget(self.ping_button)

        self.layout.addLayout(self.input_layout)

        # List widget to show results
        self.result_list = QListWidget()
        self.layout.addWidget(self.result_list)

        self.setLayout(self.layout)

    def start_ping(self):
        hosts_text = self.host_input.text()
        hosts = [h.strip() for h in hosts_text.split(",") if h.strip()]
        if not hosts:
            self.result_list.clear()
            item = QListWidgetItem("Insira os endereços IP ou nomes de host")
            self.result_list.addItem(item)
            return

        self.result_list.clear()

        for host in hosts:
            item = QListWidgetItem(f"{host}: Pinging...")
            item.setForeground(Qt.black)
            self.result_list.addItem(item)

        self.ping_button.setDisabled(True)

        # Store items indexed by host for updating
        self.items_map = {host: self.result_list.item(idx) for idx, host in enumerate(hosts)}

        # Start pinging concurrently
        for host in hosts:
            worker = PingWorker(host)
            worker.signals.result.connect(self.update_result)
            self.threadpool.start(worker)

    def update_result(self, host, status):
        item = self.items_map.get(host)
        if item:
            item.setText(f"{host}: {status}")
            if status == "On":
                item.setForeground(Qt.darkGreen)
            else:
                item.setForeground(Qt.red)

        # If all items updated, enable button
        all_done = all(
            not self.result_list.item(i).text().endswith("Pinging...")
            for i in range(self.result_list.count())
        )
        if all_done:
            self.ping_button.setDisabled(False)

    def closeEvent(self, event):
        # Clear the temporary file before quitting
        if os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)
        event.accept()  # Accept the event to close the application


def main():
    app = QApplication(sys.argv)
    window = PingApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
