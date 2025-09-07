from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
# CopyTextButton yangi Telegram Bot API’da bor. Aiogram versiyangizda bo‘lmasa, fallback ishlaydi.
try:
    from aiogram.types import CopyTextButton
    SUPPORTS_COPY_TEXT = True
except Exception:
    SUPPORTS_COPY_TEXT = False

from aiogram.filters import Command, CommandStart
import asyncio
from datetime import datetime, timedelta, time as dtime
import os

# ================== SOZLAMALAR ==================
TOKEN = "8305786670:AAHTVPYg6krEnOGi2wEX2yCovjH7R3lIpxM"    # BotFather token
DRIVERS_CHAT_ID  = -4917715168         # Haydovchilar guruhi ID (buyurtmalar)
RATINGS_CHAT_ID  = -4861064259         # 📊 Baholar log guruhi
PAYMENTS_CHAT_ID = -4925556700         # 💳 Cheklar guruhi

ADMIN_IDS = [6948926876]

CARD_NUMBER = "5614682216212664"
CARD_HOLDER = "BILOL HAMIDOV"
SUBSCRIPTION_PRICE = 99_000

bot = Bot(token=TOKEN)
dp  = Dispatcher()

# ---- Assets papka (rasmlar loyiha ichida) ----
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

CONTACT_IMAGE_PATH = os.path.join(ASSETS_DIR, "EltiBer.png")
ESLATMA_IMAGE_PATH = os.path.join(ASSETS_DIR, "ESLATMA.png")
CONTACT_IMAGE_URL  = ""   # xohlasa zahira URL

# ================== XOTIRA (RAM) ==================
user_profiles = {}   # {uid: {"name":..., "phone":...}}
drafts = {}          # {customer_id: {...}}
driver_onboarding = {}  # {uid: {"stage":..., "name":..., "car_make":..., "car_plate":..., "phone":...}}
orders = {}             # {customer_id: {...}}
driver_links = {}
pending_invites = {}    # {driver_id: {"msg_id":..., "link":...}}

# ================== LABELLAR ==================
CANCEL = "❌ Bekor qilish"
BACK   = "◀️ Ortga"
HOZIR  = "🕒 Hozir"
BOSHQA = "⌨️ Boshqa vaqt"

DRIVER_BTN  = "👨‍✈️ Haydovchi bo'lish"
CONTACT_BTN = "📞 Biz bilan bog'lanish"

CONTACT_PHONE = "+998503307707"
CONTACT_TG    = "EltiBer_admin"

# ================== KLAVIATURALAR ==================
def rows_from_list(items, per_row=3):
    return [list(map(lambda t: KeyboardButton(text=t), items[i:i+per_row])) for i in range(0, len(items), per_row)]

def keyboard_with_back_cancel(options, per_row=3, show_back=True):
    rows = rows_from_list(options or [], per_row=per_row)
    tail = []
    if show_back: tail.append(KeyboardButton(text=BACK))
    tail.append(KeyboardButton(text=CANCEL))
    rows.append(tail)
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def vehicle_keyboard():
    VEHICLES = ["Labo", "Damas", "Porter", "Isuzu", "Sprintor", "Vito"]
    return keyboard_with_back_cancel(VEHICLES, per_row=3, show_back=False)

def contact_keyboard(text="📲 Telefon raqamni yuborish"):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text, request_contact=True)]],
        resize_keyboard=True
    )

def share_phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Telefon raqamini ulashish", request_contact=True)],
            [KeyboardButton(text=BACK), KeyboardButton(text=CANCEL)]
        ],
        resize_keyboard=True
    )

def pickup_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
            [KeyboardButton(text=BACK), KeyboardButton(text=CANCEL)]
        ],
        resize_keyboard=True
    )

def order_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚖 Buyurtma berish")],
            [KeyboardButton(text=DRIVER_BTN)],
            [KeyboardButton(text=CONTACT_BTN)],
        ],
        resize_keyboard=True
    )

def when_keyboard():
    return keyboard_with_back_cancel([HOZIR, BOSHQA], per_row=2, show_back=True)

# ================== START ==================
@dp.message(CommandStart())
async def start_command(message: types.Message):
    uid = message.from_user.id
    profile = user_profiles.get(uid)

    if not profile or not profile.get("phone"):
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📞 Telefon raqamingizni yuboring", request_contact=True)]],
            resize_keyboard=True
        )
        await message.answer(
            f"Salom, {message.from_user.full_name}! 👋\n"
            "Iltimos, bir marta telefon raqamingizni yuboring:",
            reply_markup=kb
        )
    else:
        await message.answer("Quyidagi menyudan tanlang 👇", reply_markup=order_keyboard())

@dp.message(F.contact)
async def contact_received(message: types.Message):
    uid = message.from_user.id
    phone = message.contact.phone_number
    user_profiles[uid] = {"name": message.from_user.full_name, "phone": phone}
    if uid in driver_onboarding and driver_onboarding[uid].get("stage") == "phone":
        driver_onboarding[uid]["phone"] = phone if phone.startswith("+") else f"+{phone}"
        await after_phone_collected(uid, message)
        return
    await message.answer("✅ Telefon raqamingiz saqlandi.", reply_markup=types.ReplyKeyboardRemove())
    await message.answer("Endi quyidagi menyudan tanlang 👇", reply_markup=order_keyboard())

# ================== BIZ BILAN BOG‘LANISH ==================
@dp.message(F.text == CONTACT_BTN)
async def contact_us(message: types.Message):
    caption = (
        "<b>📞 Biz bilan bog'lanish</b>\n\n"
        "• Telefon: <a href=\"https://t.me/EltiBer_admin\">+998503307707</a>\n"
        "• Telegram: @EltiBer_admin"
    )
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Telegramga yozish", url=f"https://t.me/{CONTACT_TG}")]
    ])
    sent = False
    if CONTACT_IMAGE_PATH and os.path.exists(CONTACT_IMAGE_PATH):
        try:
            await message.answer_photo(photo=FSInputFile(CONTACT_IMAGE_PATH), caption=caption, parse_mode="HTML", reply_markup=ikb)
            sent = True
        except Exception:
            sent = False
    if not sent and CONTACT_IMAGE_URL:
        try:
            await message.answer_photo(photo=CONTACT_IMAGE_URL, caption=caption, parse_mode="HTML", reply_markup=ikb)
            sent = True
        except Exception:
            sent = False
    if not sent:
        await message.answer(caption, parse_mode="HTML", reply_markup=ikb)

# ================== BUYURTMA FLOW (boshlash) ==================
@dp.message(Command("buyurtma"))
async def buyurtma_cmd(message: types.Message):
    await prompt_order_flow(message)

@dp.message(F.text == "🚖 Buyurtma berish")
async def buyurtma_btn(message: types.Message):
    await prompt_order_flow(message)

async def prompt_order_flow(message: types.Message):
    uid = message.from_user.id
    profile = user_profiles.get(uid)

    if not profile or not profile.get("phone"):
        await message.answer("Iltimos, telefon raqamingizni yuboring 📞", reply_markup=contact_keyboard())
        return

    drafts[uid] = {"stage": "vehicle", "vehicle": None, "from": None, "to": None, "when": None}
    await message.answer(
        "🚚 Qanday yuk mashinasi kerak?\nQuyidagidan tanlang yoki o‘zingiz yozing:",
        reply_markup=vehicle_keyboard()
    )

@dp.message(F.text == CANCEL)
async def cancel_flow(message: types.Message):
    uid = message.from_user.id
    drafts.pop(uid, None)
    driver_onboarding.pop(uid, None)
    await message.answer("❌ Bekor qilindi.", reply_markup=order_keyboard())

# ================== HAYDOVCHI BO‘LISH (ESLATMA + ROZIMAN) ==================
@dp.message(F.text == DRIVER_BTN)
async def haydovchi_bolish(message: types.Message):
    uid = message.from_user.id
    drafts.pop(uid, None)
    driver_onboarding.pop(uid, None)

    if ESLATMA_IMAGE_PATH and os.path.exists(ESLATMA_IMAGE_PATH):
        try:
            await message.answer_photo(
                photo=FSInputFile(ESLATMA_IMAGE_PATH),
                caption="🔔 <b>ESLATMA</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

    req_text = (
        "👨‍✈️ <b>Haydovchi uchun minimal talablar</b>\n"
        "1) Faol <b>oylik obuna</b> bo‘lishi shart.\n"
        "2) Soz avtomobil (Labo/Damas/Porter/…) va amal qiluvchi guvohnoma.\n"
        "3) Telegram/telefon doimo onlayn; xushmuomala va vaqtga rioya.\n\n"
        "📦 <b>Ish tartibi</b>\n"
        "1) Buyurtma guruhdan “Qabul qilish” orqali olinadi; <b>narx/vaqt/manzil</b> — haydovchi ↔ mijoz o‘rtasida <b>bevosita</b> kelishiladi.\n"
        "2) <b>EltiBer ma’muriyati</b> narx, to‘lov va yetkazish jarayoniga <b>aralashmaydi</b> va <b>javobgar emas</b>.\n"
        "3) Borolmasangiz — darhol mijozga xabar bering va bekor qiling.\n\n"
        "⛔️ <b>Ogohlantirish:</b> soxtalashtirilgan chek yuborgan shaxsga nisbatan <b>jinoyiy javobgarlik</b> qo‘llanilishi mumkin."
    )
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Shartlarga roziman", callback_data="driver_agree")]
    ])
    await message.answer(req_text, parse_mode="HTML", reply_markup=ikb)

@dp.callback_query(F.data == "driver_agree")
async def driver_agree_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    driver_onboarding[uid] = {"stage": "name", "name": None, "car_make": None, "car_plate": None, "phone": None}
    await callback.message.answer("✍️ Iltimos, <b>Ism Familiya</b>ingizni yuboring:", parse_mode="HTML", reply_markup=keyboard_with_back_cancel([], show_back=True))
    await callback.answer()

# ================== ONBOARDING MATN KOLLEKTORI ==================
@dp.message(F.text)
async def onboarding_or_order_text(message: types.Message):
    uid = message.from_user.id
    if uid in driver_onboarding:
        st = driver_onboarding[uid].get("stage")
        txt = (message.text or "").strip()

        if st == "name":
            driver_onboarding[uid]["name"] = txt
            driver_onboarding[uid]["stage"] = "car_make"
            await message.answer("🚗 Avtomobil <b>markasi</b>ni yozing (masalan: Damas / Porter / Isuzu):", parse_mode="HTML", reply_markup=keyboard_with_back_cancel([], show_back=True))
            return

        if st == "car_make":
            driver_onboarding[uid]["car_make"] = txt
            driver_onboarding[uid]["stage"] = "car_plate"
            await message.answer("🔢 Avtomobil <b>davlat raqami</b>ni yozing (masalan: 01A123BC):", parse_mode="HTML", reply_markup=keyboard_with_back_cancel([], show_back=True))
            return

        if st == "car_plate":
            driver_onboarding[uid]["car_plate"] = txt
            driver_onboarding[uid]["stage"] = "phone"
            prof_phone = user_profiles.get(uid, {}).get("phone")
            hint = f"\n\nBizdagi saqlangan raqam: <b>{phone_display(prof_phone)}</b>" if prof_phone else ""
            await message.answer(
                "📞 Kontakt raqamingizni yuboring.\nRaqamni yozishingiz yoki pastdagi tugma orqali ulashishingiz mumkin." + hint,
                parse_mode="HTML",
                reply_markup=share_phone_keyboard()
            )
            return

        if st == "phone":
            phone = txt
            driver_onboarding[uid]["phone"] = phone if phone.startswith("+") else f"+{phone}"
            await after_phone_collected(uid, message)
            return

        return

    # Onboarding bo'lmasa — buyurtma oqimi
    await collect_flow(message)

async def after_phone_collected(uid: int, message: types.Message):
    data = driver_onboarding.get(uid, {})
    name = data.get("name", "—")
    car_make = data.get("car_make", "—")
    car_plate = data.get("car_plate", "—")
    phone = data.get("phone", "—")

    if uid in user_profiles:
        user_profiles[uid]["phone"] = phone
        user_profiles[uid]["name"] = user_profiles[uid].get("name") or name
    else:
        user_profiles[uid] = {"name": name, "phone": phone}

    price_txt = f"{SUBSCRIPTION_PRICE:,}".replace(",", " ")
    pay_text = (
        f"💳 <b>Obuna to‘lovi:</b> <code>{price_txt} so‘m</code> (1 oy)\n"
        f"🧾 <b>Karta:</b> <code>{CARD_NUMBER}</code>\n"
        f"👤 Karta egasi: <b>{CARD_HOLDER}</b>\n\n"
        f"✅ To‘lovni amalga oshirgach, <b>chek rasm</b>ini yuboring (screenshot ham bo‘ladi).\n"
        f"⚠️ <b>Ogohlantirish:</b> soxtalashtirilgan chek yuborgan shaxsga "
        f"<b>jinoyiy javobgarlik</b> qo‘llanilishi mumkin."
    )

    # 1-tap copy tugmasi (mavjud bo‘lsa) + fallback
    if SUPPORTS_COPY_TEXT:
        ikb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📋 Karta raqamini nusxalash",
                copy_text=CopyTextButton(text=CARD_NUMBER)
            )],
            [InlineKeyboardButton(text="📤 Chekni yuborish", callback_data="send_check")]
        ])
    else:
        ikb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Chekni yuborish", callback_data="send_check")]
        ])

    await message.answer(
        "Ma’lumotlaringiz qabul qilindi ✅\n\n"
        f"👤 <b>F.I.Sh:</b> {name}\n"
        f"🚗 <b>Avtomobil:</b> {car_make}\n"
        f"🔢 <b>Raqam:</b> {car_plate}\n"
        f"📞 <b>Telefon:</b> {phone}",
        parse_mode="HTML"
    )
    await message.answer(pay_text, parse_mode="HTML", reply_markup=ikb)
    driver_onboarding[uid]["stage"] = "wait_check"

@dp.callback_query(F.data == "send_check")
async def send_check_cb(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if uid not in driver_onboarding:
        await callback.answer(); return
    driver_onboarding[uid]["stage"] = "wait_check"
    await callback.message.answer("📸 Iltimos, <b>chek rasmini</b> bitta rasm ko‘rinishida yuboring (screenshot ham bo‘ladi).", parse_mode="HTML")
    await callback.answer()

# ================== CHEK LOGIKA: caption & yuborish helperlari ==================
def _make_payment_kb(driver_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"payok_{driver_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"payno_{driver_id}")
        ]
    ])

async def _build_check_caption(uid: int, data: dict) -> str:
    name      = data.get("name", "—")
    car_make  = data.get("car_make", "—")
    car_plate = data.get("car_plate", "—")
    phone     = data.get("phone", "—")
    cap = (
        "🧾 <b>Yangi obuna to‘lovi (haydovchi)</b>\n"
        f"👤 <b>F.I.Sh:</b> {name}\n"
        f"🚗 <b>Avtomobil:</b> {car_make}\n"
        f"🔢 <b>Raqam:</b> {car_plate}\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"🔗 <b>Profil:</b> <a href=\"tg://user?id={uid}\">{uid}</a>\n\n"
        f"💳 <b>Miqdor:</b> {SUBSCRIPTION_PRICE:,} so‘m\n"
        "⚠️ <i>Ogohlantirish: soxtalashtirilgan chek yuborgan shaxsga nisbatan "
        "jinoyiy javobgarlik qo‘llanilishi mumkin.</i>"
    ).replace(",", " ")
    return cap

async def _send_check_to_payments(uid: int, caption: str, file_id: str, as_photo: bool) -> bool:
    """
    Cheklar guruhiga rasm/hujjatni yuboradi, inline 'Tasdiqlash/Rad etish' tugmalari bilan.
    Agar rasmga huquq bo‘lmasa -> document sifatida urinadi.
    Bo‘lmasa admin(lar)ga DM orqali ogohlantiradi.
    """
    kb = _make_payment_kb(uid)
    try:
        if as_photo:
            await bot.send_photo(chat_id=PAYMENTS_CHAT_ID, photo=file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
        else:
            await bot.send_document(chat_id=PAYMENTS_CHAT_ID, document=file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
        return True
    except Exception as e:
        err = str(e).lower()
        if as_photo and "not enough rights to send photos" in err:
            try:
                await bot.send_document(chat_id=PAYMENTS_CHAT_ID, document=file_id, caption=caption, parse_mode="HTML", reply_markup=kb)
                return True
            except Exception as e2:
                e = e2

        note = ("\n\n⚠️ Chekni cheklar guruhiga yuborib bo‘lmadi. "
                "Guruh ruxsatlarini tekshiring yoki bu xabarni oldinga yuboring.")
        for admin in ADMIN_IDS:
            try:
                if as_photo:
                    await bot.send_photo(admin, file_id, caption=caption + note, parse_mode="HTML")
                else:
                    await bot.send_document(admin, file_id, caption=caption + note, parse_mode="HTML")
            except Exception:
                pass
        warn = f"❗️ Chekni cheklar guruhiga yuborib bo‘lmadi.\nUser: {uid}\nXato: {e}"
        for admin in ADMIN_IDS:
            try: await bot.send_message(admin, warn)
            except Exception: pass
        return False

# FOTO (gallery yoki screenshot)
@dp.message(F.photo)
async def receive_check_photo(message: types.Message):
    uid = message.from_user.id
    if uid not in driver_onboarding or driver_onboarding[uid].get("stage") != "wait_check":
        return
    data = driver_onboarding.get(uid, {})
    file_id = message.photo[-1].file_id
    caption = await _build_check_caption(uid, data)
    ok = await _send_check_to_payments(uid, caption, file_id, as_photo=True)
    if not ok:
        await message.answer("❌ Chekni log guruhiga yuborishda xatolik. Iltimos, keyinroq qayta urinib ko‘ring yoki admin bilan bog‘laning.")
        return
    await message.answer(
        "✅ Chek yuborildi. Iltimos, <b>tasdiqlashni kuting</b>.\n"
        "Tasdiqlangandan so‘ng <b>admin sizga Haydovchilar guruhi</b> silkasini yuboradi.",
        parse_mode="HTML",
        reply_markup=order_keyboard()
    )
    driver_onboarding.pop(uid, None)

# FAYL (document) sifatida — image/* bo‘lsa ham, bo‘lmasa ham
@dp.message(F.document)
async def receive_check_document(message: types.Message):
    uid = message.from_user.id
    if uid not in driver_onboarding or driver_onboarding[uid].get("stage") != "wait_check":
        return
    doc = message.document
    file_id = doc.file_id
    data = driver_onboarding.get(uid, {})
    caption = await _build_check_caption(uid, data)
    ok = await _send_check_to_payments(uid, caption, file_id, as_photo=False)
    if not ok:
        await message.answer("❌ Chekni log guruhiga yuborishda xatolik. Iltimos, keyinroq qayta urinib ko‘ring yoki admin bilan bog‘laning.")
        return
    await message.answer(
        "✅ Chek yuborildi. Iltimos, <b>tasdiqlashni kuting</b>.\n"
        "Tasdiqlangandan so‘ng <b>admin sizga Haydovchilar guruhi</b> silkasini yuboradi.",
        parse_mode="HTML",
        reply_markup=order_keyboard()
    )
    driver_onboarding.pop(uid, None)

# ================== ADMIN: Tasdiqlash/Rad etish tugmalari callbacklari ==================
async def _send_driver_invite_and_mark(callback: types.CallbackQuery, driver_id: int):
    # 1-martalik invite yaratish
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=DRIVERS_CHAT_ID,
            name=f"driver-{driver_id}",
            member_limit=1
        )
        invite_link = invite.invite_link
    except Exception as e:
        await callback.answer(f"❌ Silka yaratilmedi: {e}", show_alert=True)
        return

    # Haydovchiga DM
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Haydovchilar guruhiga qo‘shilish", url=invite_link)]
    ])
    try:
        dm = await bot.send_message(
            chat_id=driver_id,
            text=(
                "✅ <b>To‘lov tasdiqlandi.</b>\n\n"
                "Quyidagi tugma orqali <b>Haydovchilar guruhiga</b> qo‘shiling. "
                "Guruhga qo‘shilgandan so‘ng bu xabar avtomatik o‘chiriladi."
            ),
            parse_mode="HTML",
            reply_markup=ikb,
            disable_web_page_preview=True
        )
        pending_invites[driver_id] = {"msg_id": dm.message_id, "link": invite_link}
    except Exception as e:
        await callback.answer("❌ Haydovchiga DM yuborilmadi (botga /start yozmagan bo‘lishi mumkin).", show_alert=True)
        return

    # Cheklar guruhidagi xabarni 'Tasdiqlandi' deb yangilash va tugmalarni o‘chirish
    try:
        orig_cap = callback.message.caption or ""
        admin_name = callback.from_user.username or callback.from_user.full_name
        new_cap = f"{orig_cap}\n\n✅ <b>Tasdiqlandi</b> — {admin_name} • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        await bot.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            caption=new_cap,
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception:
        try:
            await bot.edit_message_reply_markup(chat_id=callback.message.chat.id, message_id=callback.message.message_id, reply_markup=None)
        except Exception:
            pass

    await callback.answer("✅ Tasdiqlandi va silka yuborildi.")

@dp.callback_query(F.data.startswith("payok_"))
async def cb_payment_ok(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Faqat admin tasdiqlashi mumkin.", show_alert=True)
        return
    try:
        driver_id = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("Xato ID.", show_alert=True); return

    await _send_driver_invite_and_mark(callback, driver_id)

@dp.callback_query(F.data.startswith("payno_"))
async def cb_payment_no(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Faqat admin rad etishi mumkin.", show_alert=True)
        return
    try:
        driver_id = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("Xato ID.", show_alert=True); return

    # Haydovchiga rad etilganiga doir DM
    try:
        await bot.send_message(
            driver_id,
            "❌ To‘lovingiz <b>rad etildi</b>.\n"
            "Iltimos, to‘g‘ri va aniq chek rasmini qaytadan yuboring.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Postni yangilash va tugmalarni olib tashlash
    try:
        orig_cap = callback.message.caption or ""
        admin_name = callback.from_user.username or callback.from_user.full_name
        new_cap = f"{orig_cap}\n\n❌ <b>Rad etildi</b> — {admin_name} • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        await bot.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            caption=new_cap,
            parse_mode="HTML",
            reply_markup=None
        )
    except Exception:
        try:
            await bot.edit_message_reply_markup(chat_id=callback.message.chat.id, message_id=callback.message.message_id, reply_markup=None)
        except Exception:
            pass

    await callback.answer("Rad etildi.")

# ================== ADMIN: /tasdiq <user_id> (qo‘lda variant, xohlasangiz qoldiring) ==================
@dp.message(Command("tasdiq"))
async def admin_confirm_payment(message: types.Message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        return

    parts = (message.text or "").strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("Foydalanish: <code>/tasdiq USER_ID</code>", parse_mode="HTML")
        return

    driver_id = int(parts[1])

    try:
        invite = await bot.create_chat_invite_link(
            chat_id=DRIVERS_CHAT_ID,
            name=f"driver-{driver_id}",
            member_limit=1
        )
        invite_link = invite.invite_link
    except Exception:
        await message.reply("❌ Taklif havolasini yaratib bo‘lmadi. Bot guruhda admin ekanini tekshiring.")
        return

    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Haydovchilar guruhiga qo‘shilish", url=invite_link)]
    ])
    try:
        dm = await bot.send_message(
            chat_id=driver_id,
            text=(
                "✅ <b>To‘lov tasdiqlandi.</b>\n\n"
                "Quyidagi tugma orqali <b>Haydovchilar guruhiga</b> qo‘shiling. "
                "Guruhga qo‘shilgandan so‘ng bu xabar avtomatik o‘chiriladi."
            ),
            parse_mode="HTML",
            reply_markup=ikb,
            disable_web_page_preview=True
        )
        pending_invites[driver_id] = {"msg_id": dm.message_id, "link": invite_link}
        await message.reply(f"✅ Silka yuborildi: <code>{driver_id}</code>", parse_mode="HTML")
    except Exception:
        await message.reply("❌ Haydovchiga DM yuborib bo‘lmadi (botga /start yozmagan bo‘lishi mumkin).")

# ================== CHAT MEMBER UPDATE: guruhga qo‘shilganda DM’ni o‘chirish ==================
@dp.chat_member()
async def on_chat_member(update: types.ChatMemberUpdated):
    try:
        if update.chat.id != DRIVERS_CHAT_ID:
            return
        old_status = update.old_chat_member.status
        new_status = update.new_chat_member.status
        user = update.new_chat_member.user
        if new_status in ("member", "administrator") and old_status in ("left", "kicked"):
            pend = pending_invites.pop(user.id, None)
            if pend:
                try:
                    await bot.delete_message(chat_id=user.id, message_id=pend["msg_id"])
                except Exception:
                    pass
                try:
                    await bot.send_message(user.id, "🎉 Guruhga muvaffaqiyatli qo‘shildingiz! Ishingizga omad.")
                except Exception:
                    pass
    except Exception:
        pass

# ================== ORTGA (onboarding + buyurtma) ==================
@dp.message(F.text == BACK)
async def back_flow(message: types.Message):
    uid = message.from_user.id

    # Onboarding ortga
    if uid in driver_onboarding:
        st = driver_onboarding[uid].get("stage")
        if st == "name":
            driver_onboarding.pop(uid, None)
            await message.answer("Asosiy menyu", reply_markup=order_keyboard()); return
        if st == "car_make":
            driver_onboarding[uid]["stage"] = "name"
            await message.answer("✍️ Iltimos, <b>Ism Familiya</b>ingizni yuboring:", parse_mode="HTML", reply_markup=keyboard_with_back_cancel([], show_back=True)); return
        if st == "car_plate":
            driver_onboarding[uid]["stage"] = "car_make"
            await message.answer("🚗 Avtomobil <b>markasi</b>ni yozing:", parse_mode="HTML", reply_markup=keyboard_with_back_cancel([], show_back=True)); return
        if st == "phone":
            driver_onboarding[uid]["stage"] = "car_plate"
            await message.answer("🔢 Avtomobil <b>davlat raqami</b>ni yozing:", parse_mode="HTML", reply_markup=keyboard_with_back_cancel([], show_back=True)); return
        if st == "wait_check":
            await after_phone_collected(uid, message); return

    # Buyurtma ortga
    d = drafts.get(uid)
    if not d:
        await message.answer("Asosiy menyu", reply_markup=order_keyboard()); return

    stage = d["stage"]
    if stage == "vehicle":
        await message.answer("🚚 Qanday yuk mashinasi kerak?\nQuyidagidan tanlang yoki o‘zingiz yozing:", reply_markup=vehicle_keyboard()); return
    if stage == "from":
        d["stage"] = "vehicle"
        await message.answer("🚚 Qanday yuk mashinasi kerak?\nQuyidagidan tanlang yoki o‘zingiz yozing:", reply_markup=vehicle_keyboard()); return
    if stage == "to":
        d["stage"] = "from"
        await message.answer("📍 Yuk **qayerdan** olinadi?\nManzilni yozing yoki “📍 Lokatsiyani yuborish” tugmasi:", reply_markup=pickup_keyboard()); return
    if stage in ("when_select", "when_input"):
        d["stage"] = "to"
        await message.answer("📦 Yuk **qayerga** yetkaziladi? Manzilni yozing:", reply_markup=keyboard_with_back_cancel([], show_back=True)); return

# ================== BUYURTMA: LOKATSIYA ==================
@dp.message(F.location)
async def location_received(message: types.Message):
    uid = message.from_user.id
    if uid not in drafts: return
    d = drafts[uid]
    if d.get("stage") != "from": return
    lat = message.location.latitude
    lon = message.location.longitude
    d["from"] = f"https://maps.google.com/?q={lat},{lon}"
    d["stage"] = "to"
    await message.answer("✅ Lokatsiya qabul qilindi.\n\n📦 Endi yuk **qayerga** yetkaziladi? Manzilni yozing:", reply_markup=keyboard_with_back_cancel([], show_back=True))

# ================== BUYURTMA KOLLEKTOR ==================
async def collect_flow(message: types.Message):
    uid = message.from_user.id
    if uid not in drafts: return
    d = drafts[uid]; stage = d["stage"]; text = (message.text or "").strip()

    if stage == "vehicle":
        d["vehicle"] = text if text else "Noma'lum"
        d["stage"] = "from"
        await message.answer("📍 Yuk **qayerdan** olinadi?\nManzilni yozing yoki “📍 Lokatsiyani yuborish”:", reply_markup=pickup_keyboard()); return

    if stage == "from":
        d["from"] = text; d["stage"] = "to"
        await message.answer("📦 Yuk **qayerga** yetkaziladi? Manzilni yozing:", reply_markup=keyboard_with_back_cancel([], show_back=True)); return

    if stage == "to":
        d["to"] = text; d["stage"] = "when_select"
        await message.answer("🕒 Qaysi **vaqtga** kerak?\nTugmalardan tanlang yoki `HH:MM` yozing.", reply_markup=when_keyboard()); return

    if stage == "when_select":
        if text == HOZIR:
            d["when"] = datetime.now().strftime("%H:%M"); await finalize_and_send(message, d); return
        if text == BOSHQA:
            d["stage"] = "when_input"
            await message.answer("⏰ Vaqtni kiriting (`HH:MM`, masalan: `19:00`):", reply_markup=keyboard_with_back_cancel([], show_back=True)); return
        if is_hhmm(text):
            d["when"] = normalize_hhmm(text); await finalize_and_send(message, d); return
        await message.answer("❗️ Vaqt formati `HH:MM` bo‘lishi kerak. Yoki tugmalarni tanlang.", reply_markup=when_keyboard()); return

    if stage == "when_input":
        if is_hhmm(text):
            d["when"] = normalize_hhmm(text); await finalize_and_send(message, d); return
        await message.answer("❗️ Noto‘g‘ri format. `HH:MM` yozing (masalan: `19:00`).", reply_markup=keyboard_with_back_cancel([], show_back=True)); return

# ================== YORDAMCHI (buyurtma) ==================
def is_hhmm(s: str) -> bool:
    try:
        datetime.strptime(s, "%H:%M"); return True
    except Exception:
        return False

def normalize_hhmm(s: str) -> str:
    try:
        t = datetime.strptime(s, "%H:%M").time(); return t.strftime("%H:%M")
    except Exception:
        return s

def phone_display(p: str) -> str:
    if not p: return "—"
    p = str(p); return p if p.startswith("+") else f"+{p}"

def group_post_text(customer_id: int, order: dict, status_note: str | None = None) -> str:
    customer_name = user_profiles.get(customer_id, {}).get("name", "Mijoz")
    base = (
        f"📦 Yangi buyurtma!\n"
        f"👤 Mijoz: {customer_name}\n"
        f"🚚 Mashina: {order['vehicle']}\n"
        f"➡️ Yo‘nalish:\n"
        f"   • Qayerdan: {order['from']}\n"
        f"   • Qayerga: {order['to']}\n"
        f"🕒 Vaqt: {order['when']}\n"
        f"ℹ️ Telefon raqami guruhda ko‘rsatilmaydi."
    )
    if status_note: base += f"\n{status_note}"
    return base

def _event_dt_today_or_now(hhmm: str, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    try:
        h, m = map(int, hhmm.split(":"))
        target = datetime.combine(now.date(), dtime(hour=h, minute=m))
    except Exception:
        return now
    return target if target > now else now

async def _sleep_and_notify(delay_sec: float, chat_id: int, text: str):
    try:
        if delay_sec > 0: await asyncio.sleep(delay_sec)
        await bot.send_message(chat_id, text, disable_web_page_preview=True)
    except asyncio.CancelledError:
        return
    except Exception:
        pass

def cancel_driver_reminders(customer_id: int):
    order = orders.get(customer_id)
    if not order: return
    tasks = order.get("reminder_tasks") or []
    for t in tasks:
        try: t.cancel()
        except Exception: pass
    order["reminder_tasks"] = []

def schedule_driver_reminders(customer_id: int):
    order = orders.get(customer_id)
    if not order or order.get("status") != "accepted": return
    driver_id = order.get("driver_id")
    if not driver_id: return

    cancel_driver_reminders(customer_id)
    now = datetime.now()
    event_dt = _event_dt_today_or_now(order["when"], now=now)
    seconds_to_event = (event_dt - now).total_seconds()
    milestones = [(3600, "⏳ 1 soat qoldi"), (1800, "⏳ 30 daqiqa qoldi"), (900, "⏳ 15 daqiqa qoldi"), (0, "⏰ Vaqti bo‘ldi")]
    base = f"{order['when']} vaqti uchun buyurtma.\nYo‘nalish: {order['from']} → {order['to']}\nMuvofiqlashtirishni unutmang."
    order["reminder_tasks"] = []
    for offset, label in milestones:
        delay = seconds_to_event - offset
        if delay < 0: continue
        text = f"{label} — {base}"
        task = asyncio.create_task(_sleep_and_notify(delay, driver_id, text))
        order["reminder_tasks"].append(task)

# ================== GURUHGA YUBORISH + MIJOZGA BEKOR TUGMASI ==================
async def finalize_and_send(message: types.Message, d: dict):
    uid = message.from_user.id
    order_data = {"vehicle": d["vehicle"], "from": d["from"], "to": d["to"], "when": d["when"]}
    ikb_group = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❗️ Qabul qilish", callback_data=f"accept_{uid}")]
    ])
    sent = await bot.send_message(DRIVERS_CHAT_ID, group_post_text(uid, order_data), reply_markup=ikb_group)
    orders[uid] = {
        **order_data, "msg_id": sent.message_id, "status": "open",
        "driver_id": None, "cust_info_msg_id": None, "drv_info_msg_id": None,
        "cust_rating_msg_id": None, "rating": None, "reminder_tasks": []
    }
    ikb_cust = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Buyurtmani bekor qilish", callback_data=f"cancel_{uid}")]
    ])
    await message.answer("✅ Buyurtma haydovchilarga yuborildi.\nKerak bo‘lsa bekor qilishingiz mumkin.", reply_markup=ikb_cust)
    await message.answer("Asosiy menyu", reply_markup=order_keyboard())
    drafts.pop(uid, None)

# ================== QABUL / YAKUN / BAHO / BEKOR ==================
@dp.callback_query(F.data.startswith("accept_"))
async def accept_order(callback: types.CallbackQuery):
    try: customer_id = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("Xato ID.", show_alert=True); return

    order = orders.get(customer_id); customer = user_profiles.get(customer_id)
    if not order or not customer:
        await callback.answer("Bu buyurtma topilmadi yoki allaqachon yakunlangan.", show_alert=True); return
    if order.get("status") != "open":
        await callback.answer("Bu buyurtma allaqachon qabul qilingan yoki yakunlangan.", show_alert=True); return

    driver_id = callback.from_user.id
    driver = user_profiles.get(driver_id)
    if not driver or not driver.get("phone"):
        await bot.send_message(driver_id, "ℹ️ Buyurtmani qabul qilishdan oldin telefon raqamingizni yuboring.", reply_markup=contact_keyboard())
        await callback.answer("Avval telefon raqamingizni yuboring.", show_alert=True); return

    order["status"] = "accepted"; order["driver_id"] = driver_id

    customer_name, customer_phone = customer.get("name", "Noma'lum"), customer.get("phone", "—")
    driver_name, driver_phone     = driver.get("name", callback.from_user.full_name), driver.get("phone", "—")

    txt_drv = (
        f"✅ Buyurtma sizga biriktirildi\n\n"
        f"👤 Mijoz: {customer_name}\n"
        f"📞 Telefon: <a href=\"tg://user?id={customer_id}\">{phone_display(customer_phone)}</a>\n"
        f"🚚 Mashina: {order['vehicle']}\n"
        f"➡️ Yo‘nalish:\n   • Qayerdan: {order['from']}\n   • Qayerga: {order['to']}\n"
        f"🕒 Vaqt: {order['when']}"
    )
    ikb_drv = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtmani yakunlash", callback_data=f"complete_{customer_id}")],
        [InlineKeyboardButton(text="❌ Buyurtmani bekor qilish", callback_data=f"cancel_{customer_id}")],
        [InlineKeyboardButton(text="👤 Mijoz profili", url=f"tg://user?id={customer_id}")]
    ])
    try:
        drv_msg = await bot.send_message(driver_id, txt_drv, parse_mode="HTML", disable_web_page_preview=True, reply_markup=ikb_drv)
        order["drv_info_msg_id"] = drv_msg.message_id
    except Exception:
        await callback.answer("Haydovchiga DM yuborilmadi. Botga /start yozing.", show_alert=True); return

    try:
        await bot.edit_message_text(chat_id=DRIVERS_CHAT_ID, message_id=order["msg_id"], text=group_post_text(customer_id, order, status_note="✅ Holat: QABUL QILINDI"))
        await bot.edit_message_reply_markup(chat_id=DRIVERS_CHAT_ID, message_id=order["msg_id"], reply_markup=None)
    except Exception:
        pass

    txt_cust = (
        f"🚚 Buyurtmangizni haydovchi qabul qildi.\n\n"
        f"👨‍✈️ Haydovchi: {driver_name}\n"
        f"📞 Telefon: <a href=\"tg://user?id={driver_id}\">{phone_display(driver_phone)}</a>"
    )
    ikb_cust = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Buyurtmani bekor qilish", callback_data=f"cancel_{customer_id}")],
        [InlineKeyboardButton(text="👨‍✈️ Haydovchi profili", url=f"tg://user?id={driver_id}")]
    ])
    try:
        cust_msg = await bot.send_message(customer_id, txt_cust, parse_mode="HTML", disable_web_page_preview=True, reply_markup=ikb_cust)
        order["cust_info_msg_id"] = cust_msg.message_id
    except Exception:
        pass

    schedule_driver_reminders(customer_id)
    await callback.answer("Buyurtma sizga biriktirildi!")

@dp.callback_query(F.data.startswith("complete_"))
async def complete_order(callback: types.CallbackQuery):
    try: customer_id = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("Xato ID.", show_alert=True); return
    order = orders.get(customer_id)
    if not order: await callback.answer("Buyurtma topilmadi.", show_alert=True); return
    driver_id = order.get("driver_id")
    if callback.from_user.id != driver_id:
        await callback.answer("Faqat ushbu buyurtmani olgan haydovchi yakunlashi mumkin.", show_alert=True); return
    if order["status"] != "accepted":
        await callback.answer("Bu buyurtma yakunlab bo‘lmaydi (holat mos emas).", show_alert=True); return

    order["status"] = "completed"
    cancel_driver_reminders(customer_id)
    drv_msg_id = order.get("drv_info_msg_id")
    if drv_msg_id:
        try: await bot.edit_message_reply_markup(chat_id=driver_id, message_id=drv_msg_id, reply_markup=None)
        except Exception: pass
    try:
        await bot.edit_message_text(chat_id=DRIVERS_CHAT_ID, message_id=order["msg_id"], text=group_post_text(customer_id, order, status_note="✅ Holat: YAKUNLANDI"))
        await bot.edit_message_reply_markup(chat_id=DRIVERS_CHAT_ID, message_id=order["msg_id"], reply_markup=None)
    except Exception: pass

    cust_info_id = order.get("cust_info_msg_id")
    if cust_info_id:
        try: await bot.delete_message(chat_id=customer_id, message_id=cust_info_id)
        except Exception: pass
        order["cust_info_msg_id"] = None

    rating_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i), callback_data=f"rate_{customer_id}_{i}") for i in range(1,6)]])
    try:
        rate_msg = await bot.send_message(customer_id, "✅ Buyurtmangiz muvaffaqiyatli yakunlandi.\nIltimos, xizmatimizni 1–5 baholang:", reply_markup=rating_kb)
        order["cust_rating_msg_id"] = rate_msg.message_id
    except Exception: pass
    await callback.answer("Buyurtma yakunlandi.")

@dp.callback_query(F.data.startswith("rate_"))
async def rate_order(callback: types.CallbackQuery):
    try: _, cust_id_str, score_str = callback.data.split("_"); customer_id = int(cust_id_str); score = int(score_str)
    except Exception:
        await callback.answer("Xato format.", show_alert=True); return
    order = orders.get(customer_id)
    if not order: await callback.answer("Buyurtma topilmadi.", show_alert=True); return
    if callback.from_user.id != customer_id:
        await callback.answer("Faqat buyurtma egasi baholay oladi.", show_alert=True); return
    if order.get("status") != "completed":
        await callback.answer("Baholash faqat yakunlangan buyurtma uchun.", show_alert=True); return

    order["rating"] = max(1, min(5, score))
    rate_msg_id = order.get("cust_rating_msg_id")
    if rate_msg_id:
        try: await bot.edit_message_reply_markup(chat_id=customer_id, message_id=rate_msg_id, reply_markup=None)
        except Exception: pass
    try: await bot.send_message(customer_id, f"😊 Rahmat! Bahoyingiz qabul qilindi: {order['rating']}/5.")
    except Exception: pass

    customer_name = user_profiles.get(customer_id, {}).get("name", "Mijoz")
    log_text = (f"📊 <a href=\"tg://user?id={customer_id}\">{customer_name}</a> mijoz sizning botingizni <b>{order['rating']}/5</b> ga baholadi.")
    try: await bot.send_message(RATINGS_CHAT_ID, log_text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception: pass
    await callback.answer("Rahmat!")

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order(callback: types.CallbackQuery):
    try: customer_id = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer("Xato ID.", show_alert=True); return
    order = orders.get(customer_id)
    if not order:
        await callback.answer("Buyurtma topilmadi yoki allaqachon bekor qilingan.", show_alert=True); return
    if order.get("status") == "completed":
        await callback.answer("Bu buyurtma yakunlangan, bekor qilib bo‘lmaydi.", show_alert=True); return

    driver_id = order.get("driver_id"); caller = callback.from_user.id

    # Mijoz bekor qildi
    if caller == customer_id:
        cancel_driver_reminders(customer_id)
        try: await bot.delete_message(chat_id=DRIVERS_CHAT_ID, message_id=order["msg_id"])
        except Exception: pass
        if driver_id:
            try: await bot.send_message(driver_id, "❌ Mijoz buyurtmani bekor qildi.")
            except Exception: pass
        try: await bot.send_message(customer_id, "❌ Buyurtmangiz bekor qilindi.")
        except Exception: pass
        orders.pop(customer_id, None)
        await callback.answer("Bekor qilindi (mijoz)."); return

    # Haydovchi bekor qildi
    if caller == driver_id:
        cancel_driver_reminders(customer_id)
        cust_info_id = order.get("cust_info_msg_id")
        if cust_info_id:
            try: await bot.delete_message(chat_id=customer_id, message_id=cust_info_id)
            except Exception: pass
            order["cust_info_msg_id"] = None
        try:
            await bot.send_message(customer_id, "❌ Buyurtmangiz haydovchi tomonidan bekor qilindi. Tez orada sizning buyurtmangizni yangi haydovchi qabul qiladi.")
        except Exception: pass
        reopen_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❗️ Qabul qilish", callback_data=f"accept_{customer_id}")]
        ])
        try:
            await bot.edit_message_text(chat_id=DRIVERS_CHAT_ID, message_id=order["msg_id"], text=group_post_text(customer_id, order, status_note=None))
            await bot.edit_message_reply_markup(chat_id=DRIVERS_CHAT_ID, message_id=order["msg_id"], reply_markup=reopen_kb)
        except Exception: pass
        drv_msg_id = order.get("drv_info_msg_id")
        if drv_msg_id:
            try: await bot.edit_message_reply_markup(chat_id=driver_id, message_id=drv_msg_id, reply_markup=None)
            except Exception: pass
        order["status"] = "open"; order["driver_id"] = None
        await callback.answer("Bekor qilindi (haydovchi)."); return

    # Admin bekor qildi
    if caller in ADMIN_IDS:
        cancel_driver_reminders(customer_id)
        try: await bot.delete_message(chat_id=DRIVERS_CHAT_ID, message_id=order["msg_id"])
        except Exception: pass
        if driver_id:
            try: await bot.send_message(driver_id, "❌ Buyurtma admin tomonidan bekor qilindi.")
            except Exception: pass
        try: await bot.send_message(customer_id, "❌ Buyurtmangiz admin tomonidan bekor qilindi.")
        except Exception: pass
        orders.pop(customer_id, None)
        await callback.answer("Bekor qilindi (admin)."); return

    await callback.answer("Bu buyurtmani bekor qilishga ruxsatingiz yo‘q.", show_alert=True)

# ================== DIAGNOSTIKA (ixtiyoriy) ==================
@dp.message(Command("test_payments"))
async def test_payments_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        await bot.send_message(PAYMENTS_CHAT_ID, "✅ Test: bot cheklar guruhiga xabar yubora oladi.")
        await message.reply("✅ OK: xabar cheklar guruhiga yuborildi.")
    except Exception as e:
        await message.reply(f"❌ Muvaffaqiyatsiz: {e}")

@dp.message(Command("test_payments_photo"))
async def test_payments_photo_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        url = "https://via.placeholder.com/600x240.png?text=Payments+Photo+Test"
        await bot.send_photo(PAYMENTS_CHAT_ID, url, caption="🧪 Test photo (payments)")
        await message.reply("✅ Rasm cheklar guruhiga yuborildi.")
    except Exception as e:
        await message.reply(f"❌ Rasm yuborilmadi: {e}")

# ================== POLLING ==================
async def main():
    print("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
