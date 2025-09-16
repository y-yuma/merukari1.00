import pyautogui
import time

print("5秒後に中クリックします")
time.sleep(5)

# メルカリの商品上でこれを実行
x, y = pyautogui.position()  # 現在のマウス位置
print(f"クリック位置: ({x}, {y})")
pyautogui.click(x, y, button='middle')
print("中クリック実行完了")
