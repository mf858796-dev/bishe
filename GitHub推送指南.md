# GitHub 推送指南

## ✅ 已完成的步骤

1. ✅ 初始化Git仓库
2. ✅ 创建.gitignore文件（排除不必要文件）
3. ✅ 添加所有文件
4. ✅ 首次提交（48个文件，13995行代码）
5. ✅ 重命名分支为main
6. ✅ 添加远程仓库

---

## 🚀 推送到GitHub的方法

### 方法1：使用HTTPS（需要GitHub账号密码或Token）

```bash
cd e:\毕设
git push -u origin main
```

**如果遇到认证问题：**

1. **使用Personal Access Token（推荐）**
   - 访问：https://github.com/settings/tokens
   - 点击"Generate new token (classic)"
   - 勾选权限：repo, workflow
   - 生成Token并复制
   - 推送时用户名输入GitHub用户名，密码输入Token

2. **使用Git Credential Manager**
   ```bash
   git config --global credential.helper manager
   git push -u origin main
   # 会弹出窗口让您登录GitHub
   ```

---

### 方法2：使用SSH（需要配置SSH密钥）

#### 步骤1：检查是否已有SSH密钥
```bash
ls ~/.ssh/id_ed25519.pub
```

如果文件不存在，创建新密钥：
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# 按回车使用默认位置
# 设置密码（可选）
```

#### 步骤2：添加SSH密钥到GitHub
1. 复制公钥内容：
   ```bash
   cat ~/.ssh/id_ed25519.pub
   # Windows PowerShell:
   Get-Content ~\.ssh\id_ed25519.pub | Set-Clipboard
   ```

2. 访问：https://github.com/settings/keys
3. 点击"New SSH key"
4. 粘贴公钥内容
5. 标题填写："My Laptop" 或其他标识
6. 点击"Add SSH key"

#### 步骤3：切换为SSH URL
```bash
cd e:\毕设
git remote set-url origin git@github.com:mf858796-dev/bishe.git
git push -u origin main
```

首次连接时会提示确认主机密钥，输入`yes`。

---

### 方法3：使用GitHub Desktop（图形界面，最简单）

1. 下载GitHub Desktop：https://desktop.github.com/
2. 安装并登录GitHub账号
3. 点击"Add an Existing Repository"
4. 选择`E:\毕设`文件夹
5. 点击"Publish repository"
6. 完成！

---

## 🔍 常见问题解决

### 问题1：Connection was reset
**原因**：网络不稳定或被防火墙阻止

**解决方案**：
```bash
# 尝试多次推送
git push -u origin main

# 或者增加超时时间
git config --global http.postBuffer 524288000
git push -u origin main
```

### 问题2：Authentication failed
**原因**：GitHub不再支持密码认证

**解决方案**：
使用Personal Access Token（见方法1）

### 问题3：Permission denied (publickey)
**原因**：SSH密钥未正确配置

**解决方案**：
1. 检查SSH密钥是否正确添加到GitHub
2. 测试SSH连接：
   ```bash
   ssh -T git@github.com
   # 应该看到：Hi username! You've successfully authenticated...
   ```

### 问题4：Updates were rejected
**原因**：远程仓库已有内容

**解决方案**：
```bash
# 强制推送（谨慎使用，会覆盖远程内容）
git push -u origin main --force

# 或者先拉取再推送
git pull origin main --allow-unrelated-histories
git push -u origin main
```

---

## 📝 当前项目状态

### 已提交的文件（48个）：
- ✅ 核心代码：main.py, main_window.py, training_widget.py等
- ✅ 模块文件：attention_model.py, coordinate_mapper.py等
- ✅ 文档文件：所有.md说明文档
- ✅ 批处理文件：启动脚本

### 已排除的文件（在.gitignore中）：
- ❌ venv/ - 虚拟环境
- ❌ data/ - 用户数据
- ❌ reports/ - 生成的报告
- ❌ *.png - 图片文件
- ❌ g3pylib/ - 嵌套Git仓库
- ❌ __pycache__/ - Python缓存

---

## 🎯 快速推送命令

如果您已经配置好认证，只需运行：

```bash
cd e:\毕设
git push -u origin main
```

系统会提示您输入：
- Username: 您的GitHub用户名
- Password: Personal Access Token（不是GitHub密码）

---

## 📊 推送后验证

推送成功后，访问以下链接查看您的仓库：
https://github.com/mf858796-dev/bishe

您应该能看到：
- ✅ 所有源代码文件
- ✅ README.md
- ✅ 所有文档
- ✅ .gitignore

---

## 💡 后续更新代码

每次修改代码后，使用以下命令推送更新：

```bash
cd e:\毕设
git add .
git commit -m "描述您的更改"
git push
```

---

## 🔐 安全建议

1. **不要提交敏感信息**
   - API密钥
   - 密码
   - 数据库连接字符串
   
2. **定期检查.gitignore**
   - 确保不包含大文件
   - 确保不包含敏感数据

3. **使用.env文件管理配置**
   ```python
   # 创建.env文件（添加到.gitignore）
   DB_PASSWORD=your_password
   API_KEY=your_key
   
   # 在代码中使用
   import os
   from dotenv import load_dotenv
   load_dotenv()
   password = os.getenv('DB_PASSWORD')
   ```

---

**祝您推送成功！** 🎉

如有问题，请检查：
1. 网络连接
2. GitHub账号状态
3. 认证方式配置
4. 防火墙设置
