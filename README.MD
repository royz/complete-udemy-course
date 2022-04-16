# Complete any udemy course in seconds (including quizzes)

#### Instructions:
1. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
2. Run the script
   ```bash
   python complete_course.py
   ```
3. Follow the instructions

Udemy has made most of their cookies http only. Which means the javascript code cannot access those cookies anymore. To get the required cookies, follow these instructions:
- Install a chrome extension called [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg?hl=en)
- While udemy is open and you are logged in, click on the cookie icon (🍪) from the extensions.
- Copy the values of `access_token` and `client_id` when asked into the terminal
