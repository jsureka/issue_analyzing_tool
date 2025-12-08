# Deployment Guide

## Deploying to Ubuntu VM

1. **Transfer the setup script** to your VM (e.g., via SCP).
   ```bash
   scp "INSIGHT Tool/setup_vm.sh" user@your-vm-ip:~/
   ```

2. **Connect to the VM** via SSH.
   ```bash
   ssh user@your-vm-ip
   ```

3. **Make the script executable**. This is required to avoid "Permission denied" errors.
   ```bash
   chmod +x setup_vm.sh
   ```

4. **Run the script with sudo**.
   ```bash
   sudo ./setup_vm.sh
   ```

5. **Follow the on-screen prompts** to configure APIs and keys.
