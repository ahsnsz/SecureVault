// 在Windows上运行
给mac中 main.py 和 app/ 文件夹 打包成一个 SecureVault_Code.zip

然后在win上安装核心库与打包文件：
  pip install customtkinter cryptography pyinstaller

然后可以进行测试：
  python main.py

退出程序回到终端进行打包，生成 .exe 文件
  pyinstaller --noconfirm --windowed --name "SecureVault" --collect-all customtkinter main.py
