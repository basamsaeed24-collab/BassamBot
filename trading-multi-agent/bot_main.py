import os
from dotenv import load_dotenv
import ccxt
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import pandas as pd
import pandas_ta as ta
import time
import threading
import csv
import json
import io
import mplfinance as mpf
from google import genai

# تحميل المتغيرات
load_dotenv()

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TRADE_AMOUNT_USDT = 5.0

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

bot = telebot.TeleBot(TELEGRAM_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT', 'SOL/USDT', 'DOT/USDT', 'DOGE/USDT',
    'AVAX/USDT', 'MATIC/USDT', 'LTC/USDT', 'LINK/USDT', 'BCH/USDT', 'XLM/USDT', 'ALGO/USDT', 'ATOM/USDT'
] # تم اختصار القائمة هنا للتوضيح، يمكنك وضع الـ 40 عملة كاملة

auto_trading_enabled = False
active_trades = {}

def save_trade(symbol, side, amount, price, note=""):
    file_exists = os.path.isfile('trade_history.csv')
    with open('trade_history.csv', mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Timestamp', 'Symbol', 'Side', 'Amount', 'Price', 'Note'])
        writer.writerow([time.strftime('%Y-%m-%d %H:%M:%S'), symbol, side, amount, price, note])

# ================= 1. المحلل البصري: رسم الشارت هندسياً =================
def generate_chart_image(df, symbol):
    try:
        df_chart = df.copy()
        df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'], unit='ms')
        df_chart.set_index('timestamp', inplace=True)
        
        # أخذ آخر 40 شمعة فقط لرؤية واضحة للنماذج الفنية
        df_chart = df_chart.tail(40)
        
        buf = io.BytesIO()
        # رسم خط الـ EMA 200 فوق الشموع
        ema_plot = mpf.make_addplot(df_chart['EMA_200'], color='blue', width=1.5, title="EMA 200")
        
        mpf.plot(df_chart, type='candle', style='yahoo', addplot=ema_plot,
                 title=f"\n{symbol} - AI Visual Analysis", volume=True, 
                 figsize=(10, 6), savefig=buf)
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Chart Error: {e}")
        return None

# ================= 2. رادار الحيتان وتحليل المشاعر بالـ AI =================
def confirm_signal_and_whales(symbol, rsi, macdh, adx, ema_200, cmf, price, vol_surge):
    try:
        prompt = f"""
        أنت محلل مالي مؤسسي. قم بتحليل هذه العملة {symbol} لاكتشاف تلاعب الحيتان (Pump & Dump) وتأكيد الدخول:
        - السعر الحالي: {price}
        - مؤشر القوة النسبية RSI: {rsi:.2f}
        - الماكد MACD: {macdh:.4f}
        - تدفق السيولة CMF: {cmf:.4f}
        - انفجار الفوليوم: {vol_surge:.2f} ضعف المتوسط الطبيعي.

        إذا كان انفجار الفوليوم مبالغاً فيه (> 3x) مع RSI مرتفع، فهذا فخ حيتان (Whale Trap).
        الرد يجب أن يكون بصيغة JSON فقط:
        {{"decision": "CONFIRMED" or "REJECTED", "manipulation_risk": "High" or "Low", "reason": "شرح قصير بالعربية لسبب الدخول أو الرفض استناداً لحركة الحيتان"}}
        """
        response = gemini_client.models.generate_content(
            model='gemini-3.5-flash-lite', 
            contents=prompt
        )
        result = json.loads(response.text.replace('```json', '').replace('```', '').strip())
        
        if result.get("decision") == "CONFIRMED" and result.get("manipulation_risk") == "Low":
            return True, result.get("reason", "فرصة آمنة")
        return False, result.get("reason", "مخاطرة تلاعب عالية")
        
    except Exception as e:
        print(f"AI Error: {e}")
        return True, "تم التمرير (خطأ في الاتصال بالذكاء الاصطناعي)"

def execute_trade(symbol, stop_loss, tp1, tp2, tp3, ai_reason, chart_buf):
    global CHAT_ID
    if symbol in active_trades: return 

    try:
        params = {'quoteOrderQty': TRADE_AMOUNT_USDT}
        buy_order = exchange.create_market_buy_order(symbol, 'buy', params)
        
        actual_amount = buy_order.get('filled', 0)
        actual_price = buy_order.get('price', buy_order.get('average', 0))
        
        if actual_price == 0 or actual_amount == 0:
            actual_price = exchange.fetch_ticker(symbol)['last']
            actual_amount = TRADE_AMOUNT_USDT / actual_price

        active_trades[symbol] = {
            'amount': actual_amount,
            'entry_price': actual_price,
            'stop_loss': stop_loss,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'current_target': 1
        }
        save_trade(symbol, 'BUY', actual_amount, actual_price, f"سبب الذكاء الاصطناعي: {ai_reason}")
        
        if CHAT_ID:
            msg = (
                f"🚀 *⚡️ تـم الـدخـول فـي صـفـقـة جـديـدة ⚡️*\n\n"
                f"🔹 *الـعـمـلـة:* `{symbol}`\n"
                f"📥 *سعر الدخول:* `{actual_price:.4f} $`\n"
                f"🐋 *تحليل الحيتان والمشاعر:* {ai_reason}\n"
                f"───────────────────\n"
                f"🔴 *SL:* `{stop_loss:.4f} $`\n"
                f"🎯 *TP1:* `{tp1:.4f} $` | 🎯 *TP2:* `{tp2:.4f} $`\n"
            )
            if chart_buf:
                bot.send_photo(CHAT_ID, photo=chart_buf, caption=msg, parse_mode="Markdown")
            else:
                bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            
    except Exception as e:
        if CHAT_ID: bot.send_message(CHAT_ID, f"❌ *خطأ شراء:* {str(e)}", parse_mode="Markdown")

def check_indicators(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df.ta.macd(append=True)
        df.ta.rsi(append=True)
        df.ta.adx(append=True)
        df.ta.ema(length=200, append=True)
        df.ta.cmf(append=True)
        
        # حساب نسبة الانفجار في السيولة (الفوليوم الحالي مقارنة بمتوسط 20 شمعة)
        avg_vol = df['volume'].tail(20).mean()
        current_vol = df['volume'].iloc[-1]
        vol_surge = current_vol / avg_vol if avg_vol > 0 else 1

        last_row = df.iloc[-1]
        rsi, macdh, adx = last_row.get('RSI_14', 50), last_row.get('MACDh_12_26_9', 0), last_row.get('ADX_14', 0)
        ema_200, cmf = last_row.get('EMA_200', 0), last_row.get('CMF_20', 0)
        current_price = exchange.fetch_ticker(symbol)['last']

        if current_price > ema_200 and cmf > 0 and rsi < 70 and macdh > 0 and adx > 25:
            sl = current_price * 0.985
            tp1, tp2, tp3 = current_price * 1.01, current_price * 1.02, current_price * 1.03
            return True, sl, tp1, tp2, tp3, rsi, macdh, adx, ema_200, cmf, current_price, vol_surge, df
            
        return False, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, None
    except:
        return False, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, None

def auto_trading_loop():
    while True:
        if auto_trading_enabled:
            for symbol in SYMBOLS:
                if symbol not in active_trades:
                    is_signal, sl, tp1, tp2, tp3, rsi, macdh, adx, ema_200, cmf, current_price, vol_surge, df = check_indicators(symbol)
                    if is_signal:
                        is_safe, reason = confirm_signal_and_whales(symbol, rsi, macdh, adx, ema_200, cmf, current_price, vol_surge)
                        if is_safe:
                            # رسم الشارت هندسياً قبل الدخول
                            chart_buf = generate_chart_image(df, symbol)
                            execute_trade(symbol, sl, tp1, tp2, tp3, reason, chart_buf)
                time.sleep(2)
        time.sleep(30)

def active_trades_monitor_loop():
    global CHAT_ID
    while True:
        try:
            symbols_to_check = list(active_trades.keys())
            for symbol in symbols_to_check:
                if symbol not in active_trades: continue
                
                trade = active_trades[symbol]
                current_price = exchange.fetch_ticker(symbol)['last']
                
                if current_price <= trade['stop_loss']:
                    exchange.create_market_sell_order(symbol, trade['amount'])
                    save_trade(symbol, 'SELL', trade['amount'], current_price, "ضرب وقف الخسارة")
                    if CHAT_ID: bot.send_message(CHAT_ID, f"🚨 ضربت عملة `{symbol}` وقف الخسارة عند `{current_price:.4f}`.", parse_mode="Markdown")
                    active_trades.pop(symbol, None)
                    continue

                target_num = trade['current_target']
                if target_num <= 3:
                    target_price = trade[f'tp{target_num}']
                    if current_price >= target_price:
                        markup = InlineKeyboardMarkup()
                        markup.row(InlineKeyboardButton("🛡️ تأمين", callback_data=f"sec_{symbol}"), InlineKeyboardButton("💰 بيع", callback_data=f"exit_{symbol}"))
                        markup.row(InlineKeyboardButton("🚀 استمرار", callback_data=f"cont_{symbol}"))
                        
                        msg = f"🎉 *تم ضرب الهدف {target_num} لعملة {symbol}*\nالسعر: `{current_price:.4f} $`"
                        if CHAT_ID: bot.send_message(CHAT_ID, msg, reply_markup=markup, parse_mode="Markdown")
                        
                        if target_num < 3: trade['current_target'] += 1
                        else:
                            exchange.create_market_sell_order(symbol, trade['amount'])
                            active_trades.pop(symbol, None)
        except Exception as e:
            pass
        time.sleep(10)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('sec_', 'exit_', 'cont_')))
def handle_trade_actions(call):
    action, symbol = call.data.split('_')
    if symbol not in active_trades: return bot.answer_callback_query(call.id, "مغلقة مسبقاً.")

    trade = active_trades[symbol]
    if action == "sec":
        trade['stop_loss'] = trade['entry_price'] * 1.001
        bot.edit_message_text(f"🛡️ تم تأمين صفقة {symbol}.", call.message.chat.id, call.message.message_id)
    elif action == "exit":
        exchange.create_market_sell_order(symbol, trade['amount'])
        active_trades.pop(symbol, None)
        bot.edit_message_text(f"💰 تم إغلاق {symbol} بنجاح", call.message.chat.id, call.message.message_id)
    elif action == "cont":
        bot.edit_message_text(f"🚀 صفقة {symbol} مستمرة للهدف القادم...", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("تشغيل/إيقاف الآلي 🤖", callback_data="toggle_auto"), InlineKeyboardButton("حالة الصفقات 📊", callback_data="status"))
    bot.send_message(message.chat.id, "أهلاً بك في بوت التداول الآلي الذكي 🚀", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['toggle_auto', 'status'])
def main_menu_handler(call):
    global auto_trading_enabled
    if call.data == 'toggle_auto':
        auto_trading_enabled = not auto_trading_enabled
        bot.send_message(call.message.chat.id, f"الآلي الآن: {'✅ يعمل' if auto_trading_enabled else '❌ متوقف'}")
    elif call.data == 'status':
        msg = "📊 *الصفقات المفتوحة:*\n" + "\n".join([f"🔹 {s}" for s in active_trades]) if active_trades else "لا توجد صفقات."
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

if __name__ == "__main__":
    threading.Thread(target=active_trades_monitor_loop, daemon=True).start()
    threading.Thread(target=auto_trading_loop, daemon=True).start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)