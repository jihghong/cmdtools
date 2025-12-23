import engine  # 只 import engine 則 engine 會 import robot 且建立 robots，則各 @command 就都建好了
from scripting import execute

def execute_raised(command):
    try: execute(command)
    except Exception as e: print(repr(e))

execute('shutdown')  # 會呼叫 engine.shutdown() 印出結果 shutdown engine
execute('overview')  # 會呼叫 for robot in engine.robots: robot.overview()
execute('overview robot1')
execute('overview robot1 robot2')
execute(['overview', 'robot1', 'robot2'])  # 可以輸入 split 過的 list of strings，因為有時候會從 sys.argv 直接帶入
execute('overview robot1.[2]')  # 會呼叫 robot1.strategies[2].overview()
execute_raised('shift 3')  # 因 explicit=True 會產生錯誤訊息
execute_raised('shift robot1 3')  # 語意是要執行 for strategy in robot1.strategies: strategy.shift(3) 但因 explicit=True 會產生錯誤訊息
execute_raised('shutdown robot1')  # engine command 不接受 id
execute_raised('overview robot1.[x]')  # id 格式錯誤
execute_raised('overview unknown')  # 不存在的 robot id
execute_raised('abc robot1.[99] 1 2 3')  # strategy index 超出範圍
execute_raised('abc 1 2')  # 參數不足
execute_raised('abc robot1.[2] X 2 3')  # 參數型別無法轉換
execute_raised('patch record 28.5')  # 參數不足
execute_raised('patch record robot1 robot2 28.5 1')  # explicit robot command 只能有一個 id
execute_raised('nosuchcmd 1 2')  # 不存在的命令
execute('shift robot1.[2] 3')  # 會執行 robot1.strategies[2].shift(3) 印出結果 shift robot.[2] float(3.0)
execute(['shift', 'robot1.[2]', '3'])  # 可以輸入 split 過的 list of strings
execute('abc 1 2 3')  # 沒帶 id 代表要執行所有 engine.robots
execute('abc robot1 1 2 3')
execute('abc robot1.[2] 1 2 3')
execute('abc robot1.[2] robot2.[0] robot3.[1] 1 2 3')
execute('abc robot1.[2] robot2 robot3 1 2 3')
execute('patch record robot1.[2] 28.5 1')
execute('patch_record robot1.[2] 28.5 1')
execute(['patch', 'record', 'robot1.[2]', '28.5', '1'])
execute(['patch_record', 'robot1.[2]', '28.5', '1'])
execute(['patch record', 'robot1.[2]', '28.5', '1'])

'''
實作注意要點：

execute('shutdown') 命令後面沒接參數，代表要執行 engine 中的 shutdown()

execute('overview') 命令後面沒接參數，且 engine 中沒有 overview()，代表要執行所有的 for robot in engine.robots: robot.overview()

execute('overview robot1') 命令後有接 robot id，代表要執行 robot1.overview()

robot id 的格式是所有字母都可以使用，例如「s.2330」、「台積電」、「台積電(2330)」等，但不能包含空白字元，以免影響 split，也不能包含 [] 以免被誤解為 strategy id

execute('overview robot1.[2]') 命令後面有接 strategy id，代表要執行 robot1.strategies[2].overview()

strategy id 的格式就是 robot id 後面加 .[n]，不符合的都可視為 robot id

execute('abc robot1.[2] 1 2 3') 會執行 robot1.strategies[2].abc(1, 2.0, '3') 而印出 abc robot1.[2] int(1) float(2.0) str('3')。其中 int(1) float(2) str('3') 的型別轉換是依據函數宣告 def abc(self, a: int, b: float, c: str) 而得來的

execute('abc robot1.[2] robot2.[0] robot3.[1] 1 2 3') 會呼叫多個 strategy id 的 abc(1, 2.0, '3')，區分 id 的方法，由函數帶 a, b, c 三個參數，得知最前面 abc 是函數名稱，最後面三個 1 2 3 分別對應三個參數，其餘中間的都是 strategy id 或 robot id

execute('abc robot1.[2] robot2 robot3 1 2 3') 中間的 id 可以參雜 robot id 或 strategy id，若為 robot id 則呼叫 for strategy in robot2.strategies: strategy.abc(1, 2.0, '3')

execute('shift robot1 3') 原本是要呼叫 for strategy in robot1.strategies: strategy.shift(3.0) 但因 shift 的 @command(explicit=True) 會產生錯誤訊息

execute('overview robot1') 和 execute('abc robot1') 的區別，因為 class Robot 有定義 def overview() 因此只呼叫 robot1.overview()，但 abc 是定義在 class Strategy 裡面的，所以後面接 robot id 代表要執行全部 for strategy in robot1.strategies

execute('patch record robot1.[2] 28.5 1') 會呼叫 patch_record(28.5, 1) 也就是名稱中的底線可以用空白代替，也可以寫成原本加底線的 execute('patch_record robot1.[2] 28.5 1')、execute(['patch', 'record', 'robot1.[2]', '28.5', '1'])、execute(['patch_record', 'robot1.[2]', '28.5', '1'])，我看最好也支援 execute(['patch record', 'robot1.[2]', '28.5', '1'])

綜上所述可知：

函數扣除最前面函數名稱和最後面對應參數後，中間的都是 id

呼叫函數前，要將參數依宣告型別先轉換成正確型別

沒有帶任何 id 代表要執行全部 engine.robots

函數如果定義在 engine，就只能帶函數的參數，不能帶 id

函數如果定義在 Robot，則只能不帶參數或只能帶 robot id

函數如果定義在 Strategy，則不帶參數代表要執行所有 engine.robots；帶 robot id 代表要執行它的所有 strategies，帶 strategy id 就是執行那個 strategy

函數若是 @command(explicit=True) 則禁止執行多個 robot id 或多個 strategy id

其中 Robot、Strategy 這兩個類別名稱是確定不會變的，但 engine 這個模組名稱，在我的應用程式中是叫做 sinogrid，因此幫我想辦法看看，若移植到不同的應用程式，最好只需小小的修改

函數名稱若為多個字以底線 _ 隔開的話，輸入的命令可以用空白代替，或原原本本地輸入底線，例如 gain_align 可以寫成 gain align

須檢查 def gain(a, b, c) 和 def gain_align(b, c) 若對於輸入 gain align b c 無法辨別它是 gain('align', b, c) 還是 gain_align(b, c) 則在建立時即要產生錯誤訊息

關於 default parameter 的處理，範例程式 class Strategy 中

@command(explicit=True)
def shift(self, value: float = 0.0): ...

和

@command
def expand(self, value: float = 0.0): ...

相比較，expand 因為沒有 explicit=True
輸入以下例子時，會分辨不出意圖為何
expand robot1 robot2 會和 expand robot1 3.0 混淆
expand robot1 會和 expand 3.0 混淆

shift 因為有 explicit=True 所以不會混淆
shift robot1.[1] 就是 shift robot1.[1] 0.0
shift robot1.[1] 3.0 就不會是 shift robot1.[1] robot2.[0]，因為禁止多 id
shift 3.0 本來就被禁止

實作的時候，也要注意 default 參數是可以用，但僅限 explicit=True 的情況，否則在建立的時候就要產生錯誤訊息

'''
