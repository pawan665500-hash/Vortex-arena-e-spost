VORTEX ARENA — UPDATE PACKAGE

इस अपडेट में:
- Admin Panel में Admin Chat / Player Support Inbox
- User Panel से Admin Chat
- पहले से मौजूद Friends / Squad Finder / Team Chat
- Admin Panel में Banner upload और Banner list
- Banner और tournament image mobile page के अंदर fit होंगे
- Admin के Live tournament पर लाल LIVE badge
- Home का featured tournament Admin द्वारा जोड़े गए tournament से आएगा
- Games list केवल database में Admin द्वारा जोड़े गए games/tournaments से बनेगी
- Player Card page और Home shortcut
- Known demo tournament rows केवल तब हटेंगे जब उनमें कोई registration या room details न हों; बाकी database rows को delete नहीं किया जाता

GitHub/Render से पहले:
1. अपनी वर्तमान GitHub files और database का backup लें।
2. इस ZIP को Extract करें।
3. user_app.py, admin_panel.py, wsgi.py और requirements.txt को project root में upload करें।
4. Render पर एक ही Web Service रखें, ताकि User और Admin एक ही database तथा uploaded banner folder उपयोग करें।
5. Start Command: gunicorn wsgi:application
6. Admin Panel URL: https://YOUR-SITE.onrender.com/admin
7. User Panel URL: https://YOUR-SITE.onrender.com/
8. Render Environment Variables में VORTEX_SECRET_KEY को लंबी random secret value दें। Admin login का temporary password तुरंत Settings में बदलें।

IMPORTANT:
- यह ZIP source-code update है; live Render site पर deploy नहीं किया गया है।
- Admin और User को एक ही VORTEX_DB_PATH और VORTEX_UPLOADS_DIR देखना चाहिए। अलग-अलग Render services की local disk अपने-आप shared नहीं होती।
- Uploaded banners तभी persistent रहेंगे जब Render में persistent disk/storage configure हो या external object storage लगाया जाए।
- Chat app के अंदर Admin support chat है; friends और teams का chat मौजूदा /social पेज पर है।
- Payment/UTR manual verification अभी भी manual है; इसे automatic gateway verification न समझें।
