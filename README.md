import os
import time
import threading
import requests
import ccxt
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
from google import genai
from PIL import Image
import matplotlib
matplotlib.use('Agg')
# ==========================================
# 1. إعدادات المفاتيح الأساسية (حط مفاتيحك هنا)
# ==========================================
API_KEY = 'المفتاح_الخاصب_به'
API_SECRET = 'المفتاح_الخاصب_به'
TELEGRAM_TOKEN = 'المفتاح_الخاصب_به'
CHAT_ID = 'المفتاح_الخاصب_به'
GEMINI_API_KEY = 'المفتاح_الخاصب_به'

# ==========================================
# 2. تهيئة المنصات
# ==========================================
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

bot = telebot.TeleBot(TELEGRAM_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 3. إعدادات البوت والذاكرة و 40 عملة
# ==========================================
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOGE/USDT', 'TRX/USDT', 'TON/USDT', 'LINK/USDT',
    'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT', 'BCH/USDT', 'SHIB/USDT',
    'LTC/USDT', 'NEAR/USDT', 'APT/USDT', 'UNI/USDT', 'ATOM/USDT',
    'ICP/USDT', 'ETC/USDT', 'RENDER/USDT', 'OP/USDT', 'INJ/USDT',
    'ARB/USDT', 'FET/USDT', 'LDO/USDT', 'SUI/USDT', 'PEPE/USDT',
    'FTM/USDT', 'SEI/USDT', 'WIF/USDT', 'GALA/USDT', 'SAND/USDT',
    'MANA/USDT', 'AAVE/USDT', 'RUNE/USDT', 'ORDI/USDT', 'TIA/USDT'
]

INITIAL_BALANCE = None
MAX_DRAWDOWN_PERCENT = 5.0
dashboard_msg_id = None
active_trades = {} # ذاكرة الصفقات المفتوحة (عشان ميشتريش العملة مرتين)

# ==========================================
# 4. دوال الحماية وإدارة رأس المال التراكمية
# ==========================================
def is_safe_to_trade():
    global INITIAL_BALANCE
    try:
        current_balance = exchange.fetch_balance()['USDT']['free']
        if INITIAL_BALANCE is None:
            INITIAL_BALANCE = current_balance
            
        drawdown = ((INITIAL_BALANCE - current_balance) / INITIAL_BALANCE) * 100
        if drawdown >= MAX_DRAWDOWN_PERCENT:
            return False, drawdown
        return True, drawdown
    except:
        return False, 0

def get_trade_amount():
    try:
        balance = exchange.fetch_balance()['USDT']['free']
        trade_amount = balance * 0.05 # دخول بـ 5% من الرصيد (Auto-Compound)
        return max(trade_amount, 5.0) # أقل حاجة 5 دولار لطلبات بينانس
    except:
        return 5.0

def is_spread_safe(symbol, max_spread_percent=0.3):
    # حماية من الانزلاق السعري لو السبريد عالي
    try:
        ticker = exchange.fetch_ticker(symbol)
        spread = ((ticker['ask'] - ticker['bid']) / ticker['bid']) * 100
        return spread <= max_spread_percent
    except:
        return False

# ==========================================
# 5. دوال الذكاء الاصطناعي والمشاعر
# ==========================================
def get_fear_greed_index():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1").json()
        return int(r['data'][0]['value']), r['data'][0]['value_classification']
    except:
        return 50, "Neutral"

def analyze_sentiment_with_ai(symbol):
    prompt = f"بصفتك متداول كريبتو محترف، ما هو التوقع السريع لعملة {symbol} اليوم بناءً على الأخبار؟ أجب بـ (إيجابي) أو (سلبي) مع سطر واحد للسبب."
    try:
        response = gemini_client.models.generate_content(model='gemini-3.8-flash', contents=prompt)
        text = response.text.lower()
        return ("إيجابي" in text or "positive" in text), response.text
    except:
        return True, "تعذر الاتصال بالذكاء الاصطناعي، تم الاعتماد على التحليل الفني."
    response = None
    for attempt in range(3):
        try:
            response = gemini_client.models.generate_content(
                model='gemini-3.8-flash', 
                contents=prompt
            )
            break 
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                time.sleep(3)
            else:
                raise e
# ==========================================
# 6. دوال التحليل الفني (قناص وفريمات)
# ==========================================
def check_trend_4h(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=20)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['EMA_20'] = ta.ema(df['close'], length=20)
        return df['close'].iloc[-1] > df['EMA_20'].iloc[-1] # السعر فوق المتوسط = صاعد
    except:
        return False

def get_weighted_signal(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['RSI'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        
        score = 0
        if df['RSI'].iloc[-1] < 35: score += 1
        if macd['MACD_12_26_9'].iloc[-1] > macd['MACDs_12_26_9'].iloc[-1]: score += 1
        if df['close'].iloc[-1] > df['close'].iloc[-2]: score += 1
        return score
    except:
        return 0

def volume_sniper(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=20)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        avg_vol = df['volume'].iloc[:-1].mean()
        curr_vol = df['volume'].iloc[-1]
        
        # انفجار سيولة 300% مع شمعة خضراء
        if curr_vol > (avg_vol * 3) and df['close'].iloc[-1] > df['open'].iloc[-1]:
            return True
        return False
    except:
        return False

# ==========================================
# 7. محرك الخروج الذكي (Smart Exit & Trailing)
# ==========================================
def manage_open_trades():
    for symbol, trade_data in list(active_trades.items()):
        try:
            current_price = exchange.fetch_ticker(symbol)['last']
            entry_price = trade_data['entry_price']
            
            # تسجيل أعلى قمة للعملة بعد الشراء
            if current_price > trade_data['highest_price']:
                trade_data['highest_price'] = current_price
                
            roi_percent = ((current_price - entry_price) / entry_price) * 100
            highest_roi = ((trade_data['highest_price'] - entry_price) / entry_price) * 100

            # 1. تأمين الأرباح (بيع 50% عند 2% ربح)
            if roi_percent >= 2.0 and trade_data['stage'] == 1:
                bot.send_message(CHAT_ID, f"🎯 **تأمين الأرباح!**\nالعملة {symbol} حققت +{round(roi_percent,2)}%.\nتم بيع نصف الكمية وترك الباقي لملاحقة الأرباح 🚀", parse_mode="Markdown")
                # exchange.create_market_sell_order(symbol, trade_data['amount'] / 2) # شيل الـ # وقت الجد
                trade_data['stage'] = 2
                
            # 2. ملاحقة الأرباح (Trailing Stop: لو السعر نزل 1% من أقصى قمة يبيع الباقي)
            elif trade_data['stage'] == 2 and (highest_roi - roi_percent) >= 1.0:
                bot.send_message(CHAT_ID, f"💰 **خروج ذكي (Trailing Stop)!**\nتم بيع باقي {symbol} على ربح +{round(roi_percent,2)}% ✅", parse_mode="Markdown")
                # exchange.create_market_sell_order(symbol, trade_data['amount'] / 2) # شيل الـ # وقت الجد
                del active_trades[symbol]
                
            # 3. وقف الخسارة القاطع لحماية الحساب (-3%)
            elif roi_percent <= -3.0:
                bot.send_message(CHAT_ID, f"🛑 **وقف خسارة مفعل!**\nالعملة {symbol} عكست بـ -3%.\nتم إغلاق الصفقة لحماية الحساب.", parse_mode="Markdown")
                # exchange.create_market_sell_order(symbol, trade_data['amount']) # شيل الـ # وقت الجد
                del active_trades[symbol] 
                
        except Exception as e:
            continue

# ==========================================
# 8. الذكاء الاصطناعي المرئي للتليجرام (Vision AI)
# ==========================================
@bot.message_handler(commands=['analyze'])
def vision_ai_chart(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "يرجى كتابة الرمز، مثال: `/analyze BTC/USDT`", parse_mode="Markdown")
            return
            
        symbol = parts[1].upper()
        bot.reply_to(message, f"جاري رسم شارت {symbol} وتحليله بالذكاء الاصطناعي بالنظر... 👁️🤖")
        
        bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        chart_file = f"chart_{symbol.replace('/','')}.png"
        mpf.plot(df, type='candle', style='charles', volume=True, savefig=chart_file)
        
        img = Image.open(chart_file)
        prompt = "أنت محلل أسواق مالية. انظر إلى هذا الرسم البياني وأخبرني هل توجد نماذج فنية واضحة؟ وهل تنصح بالشراء أم البيع حالياً بناءً على الصورة فقط؟"
        
        response = gemini_client.models.generate_content(model='gemini-3.8-flash', contents=[img, prompt])

        with open(chart_file, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=response.text[:1000])

        os.remove(chart_file)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        # هيطبع الخطأ بالتفصيل في ملف nohup.out
        print(f"❌ خطأ في رسم الشارت:\n{error_details}") 
        
        # هيبعتلك الخطأ المباشر على تليجرام عشان تعرفه فوراً
        bot.reply_to(message, f"❌ حدث خطأ برمجي:\n{str(e)}")

# ==========================================
# 9. اللوحة الحية ومحرك التداول (القلب النابض)
# ==========================================
def live_dashboard_loop():
    global dashboard_msg_id
    while True:
        try:
            balance = exchange.fetch_balance()['USDT']['free']
            safe, drawdown = is_safe_to_trade()
            fng_val, fng_status = get_fear_greed_index()
            trade_amt = get_trade_amount()
            active_count = len(active_trades)
            
            status_text = "🟢 التداول يعمل" if safe else f"🔴 طوارئ (تراجع {round(drawdown,2)}%)"
            
            text = (
                "🎛 **لوحة تحكم الوحش (Super Bot)** 🎛\n"
                "─────────────────\n"
                f"💰 **رصيد USDT:** {round(balance, 2)}\n"
                f"🛡️ **الحالة:** {status_text}\n"
                f"⚖️ **مبلغ الدخول (Auto):** {round(trade_amt, 2)} USDT\n"
                f"🧠 **السوق:** {fng_val}/100 ({fng_status})\n"
                f"📈 **صفقات مفتوحة حالياً:** {active_count}\n"
                "─────────────────\n"
                f"🔄 *محدث:* {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                "لتصوير وتحليل شارت: `/analyze BTC/USDT`"
            )
            
            if dashboard_msg_id is None:
                msg = bot.send_message(CHAT_ID, text, parse_mode="Markdown")
                dashboard_msg_id = msg.message_id
            else:
                bot.edit_message_text(text, chat_id=CHAT_ID, message_id=dashboard_msg_id, parse_mode="Markdown")
                
            time.sleep(60) # تحديث كل دقيقة
        except:
            time.sleep(60)
def main_trading_engine():
    bot.send_message(1039136464, "🚀 **تم تشغيل محرك التداول وبدأ مسح 40 عملة...**", parse_mode="Markdown")
    while True:
        manage_open_trades() # فحص الصفقات المفتوحة عشان نبيع الأول
        
        safe, _ = is_safe_to_trade()
        if not safe:
            time.sleep(3600)
            continue
            
        for symbol in SYMBOLS:
            time.sleep(2) # مهم جداً جداً عشان بينانس متعملكش بلوك بسبب الـ 40 عملة
            
            if symbol in active_trades:
                continue # لو شاريين العملة دي ومفتوحة، متشتريهاش تاني
                
            if not is_spread_safe(symbol):
                continue
                
            if not check_trend_4h(symbol):
                continue 
                
            sig_score = get_weighted_signal(symbol)
            sniper_active = volume_sniper(symbol)
            
            if sig_score >= 2 or sniper_active:
                is_positive, ai_reason = analyze_sentiment_with_ai(symbol)
                
                if is_positive:
                    amt = get_trade_amount()
                    try:
                        current_price = exchange.fetch_ticker(symbol)['last']
                        coin_amount = amt / current_price
                        
                        msg = (
                            f"🚨 **إشارة دخول قوية!** 🚨\n"
                            f"🪙 **العملة:** {symbol}\n"
                            f"🧠 **تحليل AI:** {ai_reason}\n"
                            f"💸 **المبلغ:** {round(amt, 2)} USDT\n"
                            f"🎯 **سعر الدخول:** {current_price}\n"
                            f"⚡ **الاستراتيجية:** {'قناص سيولة 💥' if sniper_active else 'إشارات فنية 📊'}"
                        )
                        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
                        
                        # التنفيذ الفعلي (شيل الـ # لما تحب تشغل بفلوس حقيقية)
                        # exchange.create_market_buy_order(symbol, coin_amount)
                        
                        # إضافة العملة لذاكرة البوت لمتابعة البيع
                        active_trades[symbol] = {
                            'entry_price': current_price,
                            'amount': coin_amount,
                            'highest_price': current_price,
                            'stage': 1
                        }
                    except Exception as e:
                        print("Error in buying:", e)
                        
                    time.sleep(10) # راحة بعد الشراء
        time.sleep(15) # راحة بعد لفة الـ 40 عملة

# ==========================================
# 10. تشغيل البوت (The Start)
# ==========================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "🤖 أهلاً يا زعيم! نظام التداول الخارق جاهز.\nجاري تشغيل اللوحة الحية ومراقبة الـ 40 عملة...")
    threading.Thread(target=live_dashboard_loop, daemon=True).start()
    threading.Thread(target=main_trading_engine, daemon=True).start()

print("Super Bot V_Master 40-Coins is Running...")
bot.infinity_polling()
