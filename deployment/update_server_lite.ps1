# Update Script for Jobscout Lite on AWS
# usage: .\deployment\update_server_lite.ps1

$EC2_IP = "63.176.62.157"
$KEY_PATH = "$env:USERPROFILE\Downloads\jobscout-key.pem"
$ZIP_NAME = "jobscout_lite_update.zip"

Write-Host "Starting Jobscout Lite deployment..." -ForegroundColor Cyan

# 1. Zip the current code
Write-Host "Zipping files..." -ForegroundColor Yellow
if (Test-Path $ZIP_NAME) { Remove-Item $ZIP_NAME }

# Exclude unnecessary files
$exclude = @("venv", "__pycache__", ".git", ".env", "*.db", "*.zip", "deployment", "*.pdf", "export_pdf.py")
Compress-Archive -Path * -DestinationPath $ZIP_NAME -Force

# 2. Upload to server
Write-Host "Uploading to $EC2_IP..." -ForegroundColor Yellow
scp -i $KEY_PATH $ZIP_NAME ubuntu@${EC2_IP}:~

# 3. Remote commands: Setup, Unzip and Restart
Write-Host "Setting up server and restarting..." -ForegroundColor Yellow

$commands = @"
# Ordner erstellen falls nicht vorhanden
mkdir -p jobscout_lite
sudo apt-get install -y unzip

# Entpacken
unzip -o $ZIP_NAME -d jobscout_lite/
rm $ZIP_NAME

# Virtual Environment Setup
cd jobscout_lite
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# .env Datei vom Hauptprojekt kopieren falls nicht vorhanden (für den API Key)
if [ ! -f ".env" ]; then
    cp /home/ubuntu/jobscout/.env .env
fi

# Supervisor Konfiguration kopieren
sudo cp deployment/supervisor_lite.conf /etc/supervisor/conf.d/jobscout_lite.conf
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart jobscout_lite

echo 'Deployment Complete!'
"@

$linux_commands = $commands.Replace("`r", "")
ssh -i $KEY_PATH ubuntu@$EC2_IP $linux_commands

# 4. Cleanup local zip
if (Test-Path $ZIP_NAME) { Remove-Item $ZIP_NAME }

Write-Host "Jobscout Lite deployed successfully!" -ForegroundColor Green
Write-Host "Visit: http://$EC2_IP:5001" -ForegroundColor Cyan
