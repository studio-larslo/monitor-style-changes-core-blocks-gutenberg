Made this https://github.com/studio-larslo/monitor-style-changes-core-blocks-gutenberg
repo. It makes use of github workflows to monitor the gutenberg repo. 
Usually the changeslogs of a new Gutenberg Plugin release is bloated with links to lengthy discussions, some rather seldom used features and I quickly go TLDR;

Once a day it fetches the latest commit, checks if there where changes to 'frontend' code (i.e. changes in scss and view.js files in `packages/block-editor/src/`) and if there are any it sends an email.
**Why:** Even after years the Gutenberg team still changes the markup, styles or views.js of core blocks. When websites have auto-update enabled this might change the appearance of the site and lead to unchecked changes in layout.  So this monitoring script tries prevent you as a site owner from glitches on the frontend of your sites.
#micro-blog #writing 

## GH Secrets
gh secret set MONITOR_TOKEN
gh secret set SMTP_SERVER
gh secret set SENDER_EMAIL
gh secret set RECEIVER_EMAIL
gh secret set EMAIL_PASSWORD