VORTEX ARENA - SHOP MANAGER + VISITOR COUNTER PATCH

Is ZIP mein user_app.py aur admin_panel.py dono updated hain.

1) Backup: deploy se pehle Render persistent disk / SQLite database ka backup lein.
2) Dono Python files ko project mein replace karein; requirements.txt aur wsgi.py ko preserve karein.
3) Admin Panel mein Shop Manager route /shop-manager hai. Agar menu mein nahi dikhe to /shop-manager directly open karke dekhein.
4) Website Visitors route /visitors hai. Admin login ke baad /visitors open karein. Anonymous visits aur page views deployment ke baad se count honge; purane visits recover nahi ho sakte.
5) User Panel aur Admin Panel ko SAME shared SQLite DB path (VORTEX_DB_PATH) par point karna zaroori hai, aur Render par persistent disk chahiye; alag databases honge to visitor counts share nahi honge.
6) Syntax check kiya gaya; live Render database ke saath runtime test nahi hua. Pehle staging/backup ke saath deploy karein.
