VORTEX ARENA — CHAT + LIVE UPDATE

इस ZIP में मौजूदा User Panel और Admin Panel के अपडेटेड Python source हैं। पुराने फीचर हटाने के बजाय additive बदलाव किए गए हैं।

नए बदलाव:
1. User Panel के नीचे Chat बटन: Admin को message भेजने और किसी registered player को चुनकर message भेजने की सुविधा।
2. User Panel के ऊपर Support बटन: Discord invite, WhatsApp support और UPI ID वाला अलग Support पेज।
3. Admin Panel में Chat Inbox: खिलाड़ी के messages देखना और reply भेजना।
4. Admin Panel में Live Control: tournament status Upcoming / Live / Completed बदलना।
5. User Home पर Admin के Live किए tournament, stream button, upcoming tournaments, announcements और banner URLs दिखाने की व्यवस्था।
6. Shared tables के लिए CREATE TABLE IF NOT EXISTS और additive column migrations; existing tables DROP नहीं की जातीं।

लिंक:
Discord invite: https://discord.gg/pY9dvhaxs
WhatsApp Support: https://wa.me/9187966744832
Contact/UPI number: 8796674832
UPI ID: 8796674832@fam
YouTube: https://youtube.com/@smaltanime_00

लोकल रन:
python -m pip install -r requirements.txt
python user_app.py        # User panel on port 8082
python admin_panel.py     # Admin panel on port 8083

पहली बार Admin credentials: admin / ChangeMe-123!
लॉगिन के तुरंत बाद Settings से password बदलें। Production में VORTEX_SECRET_KEY environment variable सेट करें।

महत्वपूर्ण सीमाएँ:
- इस environment में Flask install नहीं था, इसलिए live HTTP/browser test नहीं हो पाया। Python syntax compilation check पास हुआ।
- Chat page-refresh आधारित है, WebSocket real-time नहीं। Player-to-player messages send होते हैं; वर्तमान UI में पूरा per-person threaded conversation view अभी सीमित है।
- User और Admin दोनों को same local SQLite file तभी दिखेगी जब दोनों scripts उसी persistent filesystem/folder में हों। अलग Render services में SQLite अपने-आप साझा नहीं होती; PostgreSQL जैसी shared DB configure करनी होगी।
- Live Control status बदलता है; live दिखने के लिए tournament में सही YouTube URL भी भरें।
- Banner URL के लिए admin-side persistent upload flow इस update में नहीं जोड़ा गया है।
