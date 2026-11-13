# MiniMinds setup (all free)
1. github.com -> new PUBLIC repo `miniminds`; upload these files (keep folder structure).
2. Instagram app -> Settings -> Account type -> switch to Professional (Creator). Free.
3. developers.facebook.com -> create app (type Business) -> add "Instagram" product -> API setup with Instagram login
   -> add your account as tester, accept it in Instagram (Settings > Website permissions > Tester invites)
   -> generate token (permissions: instagram_business_basic, instagram_business_content_publish, instagram_business_manage_comments, instagram_business_manage_insights). Copy token + Instagram user ID.
4. aistudio.google.com -> Get API key (free). pexels.com/api -> free key.
5. Repo -> Settings -> Secrets and variables -> Actions -> add: GEMINI_KEY, PEXELS_KEY, IG_TOKEN, IG_USER_ID.
6. Repo -> Settings -> Pages -> Deploy from branch main, folder /docs. Edit YOUR_GITHUB_USERNAME in docs/index.html.
7. Actions tab -> "MiniMinds auto-post" -> Run workflow (test). Then it runs daily by itself.
8. Pixel 10a: open https://USERNAME.github.io/miniminds in Chrome -> menu -> Add to Home screen.
Token lasts ~60 days: refresh via https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=TOKEN and update the secret.
