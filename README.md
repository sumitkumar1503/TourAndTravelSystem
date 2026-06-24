# TravelBot — AI-Powered Flight & Hotel Booking Chatbot

A complete Python full-stack web application that lets users search, compare,
and book flights and hotels through both a traditional UI and a conversational
chatbot powered by Natural Language Processing.

Built with **Django 5+**, **Bootstrap 5**, **NLTK**, **reportlab**, and **SQLite**.

---

## ✨ Features

### 👤 User module
- Registration, login, logout (Django auth)
- Profile management (avatar, address, phone, language preference)
- Loyalty tier badge (Bronze / Silver / Gold / Platinum)
- Booking history with cancel + automatic refund flow
- **Personal referral code** to share with friends
- Dark / light theme toggle
- Per-user in-app **notification bell** (bookings, promos, system)

### 🎫 Booking module
- Flight search with filters (origin, destination, date, cabin class)
- Hotel search with filters (city, dates, stars, rooms, guests)
- Hotel detail pages with **guest reviews & 5-star ratings**
- **Wishlist / favourites** for both flights and hotels
- Real-time availability (seats / rooms decrement on confirmation)
- **Promo code / coupon system** with percent or flat discounts
- **Travel-insurance addon** at checkout
- **Loyalty points** — earn 1 pt / ₹100 spent, redeem 1 pt = ₹1 off
- Dummy payment gateway (Card / UPI / Netbanking / Wallet)
- **PDF e-ticket download** (reportlab) on confirmed bookings
- Booking confirmation page with reference & transaction ID

### 🤖 Chatbot module
- Floating chat widget on every customer page
- **Voice input** via Web Speech API (mic button)
- NLP intent classification: `greet`, `search_flight`, `search_hotel`,
  `recommend`, `show_bookings`, `help`, `cancel`, `goodbye`, `thanks`,
  `promo`, `loyalty`, `wishlist`
- Entity extraction: cities, dates ("tomorrow", "next Friday", "25 Dec"),
  passengers, rooms, cabin class, star rating, budget
- Returns rich flight & hotel cards directly inside the chat
- Conversation history stored per user / session

### 🛠 Admin module (custom dashboard at `/dashboard/`)
- KPI overview — users, bookings, revenue, reviews, chat sessions
- **Full CRUD for Flights** (add / edit / delete / activate)
- **Full CRUD for Hotels** (add / edit / delete / activate)
- **Full CRUD for Coupons / promo codes** (with auto-broadcast notifications)
- **User management** — view detail, activate/deactivate, toggle staff, delete
- **Booking management** — filter, search, change status, delete
- **Contact messages** inbox with resolve toggle
- **Newsletter subscriber** list
- Reports — 30-day revenue trend, top customers, average booking value
- Admins **don't see customer features** (no chatbot widget, no booking,
  no wishlist) — they are redirected to the dashboard.

### 📄 Informational pages
- About / FAQ / Contact (with stored messages going to dashboard inbox)
- Newsletter subscription (footer)
- Quick currency converter widget on the homepage

---

## 🧰 Tech stack

| Layer       | Tech                                                |
|-------------|-----------------------------------------------------|
| Frontend    | HTML5 · CSS3 · JavaScript · Bootstrap 5 · Chart.js  |
| Backend     | Python 3.10+ · Django 5+                            |
| Database    | SQLite                                              |
| AI / NLP    | NLTK + custom rule-based engine                     |
| PDF tickets | reportlab                                           |
| Voice       | Web Speech API (browser-native)                     |

---

## 🚀 Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py migrate

# 3. Seed sample flights, hotels, coupons, and demo users
python manage.py seed_data

# 4. Start the dev server
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in your browser.

### Demo accounts

| Role  | Username | Password    | Lands on             |
|-------|----------|-------------|----------------------|
| Admin | `admin`  | `admin123`  | `/dashboard/`        |
| User  | `demo`   | `demo12345` | `/` (customer home)  |

### Sample promo codes (auto-seeded)

| Code       | Discount             | Applies to          |
|------------|----------------------|---------------------|
| `WELCOME10`| 10 % off (cap ₹1000) | Flights & hotels    |
| `FLAT500`  | ₹500 flat off        | Bookings above ₹3000|
| `FLY20`    | 20 % off (cap ₹2000) | Flights only        |
| `STAY15`   | 15 % off (cap ₹1500) | Hotels only         |
| `SUMMER25` | 25 % off (cap ₹3000) | Bookings above ₹5000|

---

## 📁 Project structure

```
Flight-and-Hotel/
├── manage.py
├── requirements.txt
├── travel_chatbot/            # Project settings
│   ├── settings.py
│   └── urls.py
├── accounts/                  # Registration, login, profile, loyalty
├── booking/                   # Flights, hotels, bookings, payments
│   ├── models.py              # +Coupon, HotelReview, Wishlist, Notification
│   ├── pdf_utils.py           # E-ticket generator (reportlab)
│   ├── templatetags/
│   │   ├── booking_extras.py  # get_item, stars filters
│   │   └── notifications.py   # navbar bell dropdown
│   └── management/commands/seed_data.py
├── chatbot/                   # NLP engine + chat API
│   └── nlp_engine.py
├── dashboard/                 # Custom admin dashboard with CRUD
│   ├── forms.py
│   ├── views.py
│   └── urls.py
├── templates/                 # All HTML templates
└── static/                    # CSS + JS (chatbot, dark mode, main)
```

---

## 💬 Sample chatbot queries

The bot understands natural-language queries like:

- "Find flights from Delhi to Goa tomorrow"
- "Show me business class flights from Mumbai to Bengaluru next Friday"
- "Hotels in Manali for 3 nights, 4 stars, under ₹6000"
- "Recommend a destination for the weekend"
- "Any promo codes?"
- "How many loyalty points do I have?"
- "Show my wishlist"
- "My bookings"

---

## 🗄️ Database schema (high level)

| Model              | Purpose                                              |
|--------------------|------------------------------------------------------|
| User               | Built-in `auth.User`                                 |
| UserProfile        | Phone, address, gender, avatar, language, loyalty    |
| Flight             | Airline, route, schedule, cabin, price, availability |
| Hotel              | Name, city, stars, amenities, price, availability    |
| Booking            | Reference, type, totals, coupon, insurance, status   |
| Payment            | Method, transaction id, status                       |
| Coupon             | Code, percent/flat discount, validity, usage limit   |
| HotelReview        | Rating + comment + verified-stay flag                |
| WishlistItem      | Saved flights/hotels per user                        |
| Notification       | In-app notifications (booking, promo, system)        |
| NewsletterSubscriber | Footer signup list                                 |
| ContactMessage     | Submitted from Contact page                          |
| ChatSession        | Per-user / per-session conversation                  |
| ChatMessage        | Each message + detected intent + entities            |

---

## 🌱 Future enhancements

- Multi-language chatbot (translate intent + replies)
- Real-time external flight / hotel APIs (Amadeus, RapidAPI)
- OpenAI fallback for free-form questions
- Real email + SMS booking confirmations (SendGrid / Twilio)
