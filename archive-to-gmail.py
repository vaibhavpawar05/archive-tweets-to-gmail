import snscrape.modules.twitter as sntwitter
import requests
import re
import uuid
from bs4 import BeautifulSoup

def download_file(url):
    r = requests.get(url)
    if r.status_code == 200:
        return r.content
    else:
        print('download failed')

def create_tweet_html_for_gmail(tweet, is_quoted=False, tweet_idx=0, test=True):
    # author block
    # link to the profile image
    if tweet_idx == 0:
        author_block = f"""
            <tr>
                <td style="width: 100%;">
                    <a href="https://twitter.com/{tweet.user.username}" style="font-size:16px;">
                        <img style="height: 48px; width: 48px; float: left; border-radius: 100%; margin-right: 6px; margin-bottom: 8px;" src="{tweet.user.profileImageUrl}">
                        <b style="display: block;margin-bottom: 2px;">{tweet.user.displayname}</b>@{tweet.user.username}
                    </a>
                </td>
            </tr>
        """
        
        time_block = f"""
            <tr>
                <td style="width: 100%;">
                    <div class="time">
                        <a href="{tweet.url}">{tweet.date:%b %d, %Y at %X}</a>
                    </div>
                </td>
            </tr>
        """

    # content block
    content = tweet.content
    
    # replace t.co links with full links
    url_extract_pattern = "https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"
    all_urls = re.findall(url_extract_pattern, tweet.content)
    
    outlinks = tweet.outlinks
    tcooutlinks = tweet.tcooutlinks
    
    if outlinks:
        num_outlinks = len(tcooutlinks)
    else:
        num_outlinks = 0
        tcooutlinks = []
        
    def create_display_link(url, max_len=25):
        url_ = url.split('://')[1]
        if len(url_) >= max_len:
            display_link = url_[0:max_len] + '...'
        else:
            display_link = url_
        return f"""<a href="{url}">{display_link}</a>"""
        
    if outlinks:
        for i, tcol in enumerate(tcooutlinks):
            content = content.replace(tcol, create_display_link(outlinks[i]))
            
    if len(all_urls) > num_outlinks:
        diff = set(all_urls) - set(tcooutlinks)
        if len(diff) == 1:
            content = content.replace(diff.pop(), '')
                    
    # get mentioned users and replace with handle block
    if tweet.mentionedUsers:
        mentioned_users = {f"@{u.username}":f"""<a href="https://twitter.com/{u.username}"><span>@{u.username}</span></a>""" for u in tweet.mentionedUsers}
        for u in mentioned_users:
            content = content.replace(u, mentioned_users[u])
            
    # replace new lines
    content = content.replace('\n', '<br>')
    
    content_block = f"""
        <tr>
            <td style="width: 100%;">
                <div style="font-size: 20px; margin:0; padding-top: 8px; line-height: 24px;">
                    {content}
                </div>
            </td>
        </tr>
    """
    
    # media block
    media_block = ''
    tweet_media = dict()
    if tweet.media:
        for m in tweet.media:

            if isinstance(m, sntwitter.Photo):
                image_name = f"""{m.fullUrl.split('/')[4].replace('?format=', '.').replace('&name=large', '')}"""
                if test:
                    src = m.fullUrl
                else:
                    src = f"cid:{image_name.split('.')[0]}"
                    tweet_media[image_name.split('.')[0]] = download_file(m.fullUrl)
                
                media_block += f"""
                    <tr>
                        <td>
                            <div class="media">
                                <img style="width:100%" src="{src}">
                            </div>
                        </td>
                    </tr>
                """

            if isinstance(m, sntwitter.Video):
                for variant in m.variants:
                    if variant.contentType == 'video/mp4':
                        video_url = variant.url
                        
                        media_block += f"""
                            <tr>
                                <td>
                                    <div class="video">
                                        <a href="{video_url}" style="font-size:20px;">Video</a>
                                    </div>
                                </td>
                            </tr>
                        """

                        break
                        
    # quoted tweet
    if tweet.quotedTweet:
        quote_block, quote_media = create_tweet_html_for_gmail(tweet.quotedTweet, assets_path, is_quoted=True, tweet_idx=0, test=test)
        
    if is_quoted:
        # wrap all blocks within class:quoted-tweet
        tweet_html = f"""
            <!-- quoted tweet -->
            <tr>
                <td>
                    <div class="quoted-tweet">
                        <table style="border-collapse: collapse; margin-left: auto; margin-right: auto;">
                            <tbody>
                                {author_block}
                                {time_block}
                                {content_block}
                                {media_block}
                            </tbody>
                        </table>
                    </div>
                </td>
            </tr>
        """
        return tweet_html, tweet_media
    else:
        # wrap all blocks within class:static-tweet-embed
        if tweet.quotedTweet:
            if tweet_idx == 0:
                tweet_html = f"""
                    {author_block}
                    {time_block}
                    {content_block}
                    {media_block}
                    {quote_block}
                """
            else:
                tweet_html = f"""
                    {content_block}
                    {media_block}
                    {quote_block}
                """
            tweet_media = {**tweet_media, **quote_media}
            return tweet_html, tweet_media
        else:
            if tweet_idx == 0:
                tweet_html = f"""
                    {author_block}
                    {time_block}
                    {content_block}
                    {media_block}
                """
            else:
                tweet_html = f"""
                    {content_block}
                    {media_block}
                """
            return tweet_html, tweet_media

def create_thread_html_for_gmail(tweet_id, assets_path):
    
    # get the scroll of the thread
    mode_scroll = sntwitter.TwitterTweetScraperMode.SCROLL
    scroll = sntwitter.TwitterTweetScraper(tweet_id, mode=mode_scroll)
    scroll_tweets = [tweet for tweet in scroll.get_items()]
    scroll_tweets_ids = [tweet.id for tweet in scroll_tweets]
    scroll_tweets_userids = [tweet.user.id for tweet in scroll_tweets]
    scroll_tweets_inreplytoids = [tweet.inReplyToTweetId for tweet in scroll_tweets]
    
    # find first and last tweet
    ## find the idx of the current tweet
    input_tweet_idx = scroll_tweets_ids.index(tweet_id)
    input_tweet_userid = scroll_tweets_userids[input_tweet_idx]
    num_tweets = len(scroll_tweets_ids)
    
    ## traverse forward and backward to find
    # forward
    i = input_tweet_idx + 1
    forward_idx = None

    while i < num_tweets:
        if scroll_tweets_userids[i] != input_tweet_userid or scroll_tweets_inreplytoids[i] != scroll_tweets_ids[i-1]:
            forward_idx = i - 1
            break
        i += 1

    if forward_idx is None:
        forward_idx = num_tweets - 1
        
    # backward
    i = input_tweet_idx - 1
    backward_idx = None

    while i >= 0:
        if scroll_tweets_userids[i] != input_tweet_userid or scroll_tweets_ids[i] != scroll_tweets_inreplytoids[i+1]:
            backward_idx = i + 1
            break
        i -= 1

    if backward_idx is None:
        backward_idx = 0
        
    # process the tweets to create their markdown and append those
    thread_html = ""
    thread_media = dict()
    thread_author = scroll_tweets[backward_idx].user
    for idx, tweet in enumerate(scroll_tweets[backward_idx:forward_idx+1]):
        tweet_html, tweet_media = create_tweet_html_for_gmail(tweet, assets_path, is_quoted=False, tweet_idx=idx, test=False)
        thread_media = {**thread_media, **tweet_media}
        thread_html = thread_html + '\n' + tweet_html
        
    thread_html = f"""
        <div class="static-tweet-embed">
            <table style="border-collapse: collapse; margin-left: auto; margin-right: auto;">
                <tbody>
                    {thread_html}
                </tbody>
            </table>
        </div>
    """
        
    return thread_html, thread_media, f"{thread_author.displayname} (@{thread_author.username})"

def save_thread_to_gmail(tweet_id, sender_email, receiver_email, password):

    message = MIMEMultipart("alternative")
    message["From"] = sender_email
    message["To"] = receiver_email

    # Create the plain-text and HTML version of your message
    text = """\
    This is a twitter thread
    """

    with open('tweet-html-for-gmail-template.html', 'rb') as f:
        html_template = f.read().decode('utf-8')

    thread_html_body, thread_media, thread_author = create_thread_html_for_gmail(tweet_id, 'test')
    
    message["Subject"] = f"Twitter Thread by {thread_author}"

    html = html_template.replace('{tweet_body}', thread_html_body)

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    for media in thread_media:
        img = MIMEImage(thread_media[media])
        img.add_header('Content-Id', f"<{media}>")
        message.attach(img)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )
