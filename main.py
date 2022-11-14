import json
from archive_to_gmail import save_thread_to_gmail

with open('bookmarks.json', 'rb') as f:
    bookmark_json = json.loads(f.read().decode('utf-8'))
    
bookmark_tweet_ids = list(bookmark_json['globalObjects']['tweets'].keys())

sender_email = "username@gmail.com"
receiver_email = "username@gmail.com"
password = input("Type your gmail password and press enter:")

for tweet_id in bookmark_tweet_ids:
    try:
        save_thread_to_gmail(int(tweet_id), sender_email, receiver_email, password)
        print(f'done {tweet_id}')
    except:
        print(f'failed for {tweet_id}')
