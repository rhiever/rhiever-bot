import praw, os, time, sys
from collections import defaultdict
from datetime import datetime, timedelta

lowPrioritySubs = ["pics", "gaming", "games", "worldnews", "videos", "todayilearned", "iama", "funny", "askreddit", "atheism", "politics", "science", "technology", "wtf", "bestof", "adviceanimals", "music", "aww", "askscience", "movies"]

submissionQueue = {}

if len(sys.argv) < 3:
    sys.stdout.write("\nBot script expects two parameters: bot username and password\n\n")
    sys.stdout.write("Usage: python rhiever-bot.py USERNAME PASSWORD\n\n")
    quit()

r = praw.Reddit(user_agent="bot by /u/" + sys.argv[1])

def checkQueue():
    """returns True if there are requests waiting in the /r/MUWs queue, False otherwise"""
    requestsWaiting = False
    for submission in r.get_subreddit("MUWs").get_new(limit=50):
        if submission.link_flair_text is None and "[request]" in submission.title.lower() and "r/all" not in submission.title.lower():
            requestsWaiting = True
            break
        
    return requestsWaiting


def fillQueue():
    """Fills the submission queue with valid requests. Removes invalid submissions."""
    
    # build submission queue to give priority to older requested posts
    global submissionQueue
    submissionQueue = {}

    for submission in r.get_subreddit("MUWs").get_new(limit=100):
        if submission.link_flair_text is None:
            if "[request]" in submission.title.lower():
                
                # debugging
                #if not (submission.author.name == "rhiever"):
                #    continue
                
                timestamp = submission.created_utc

                # just queue user requests
                if "u/" in submission.title.lower():
                    pass
                else:
                    # check if requested sub is a low priority sub
                    title = submission.title.lower().split("r/")
                    title = title[1].split(" ")
                    title = title[0].lower()

                    # do NOT accept requests for /r/all
                    if title == "all":
                        sys.stderr.write("skipped /r/all\n")
                        continue

                    if title in lowPrioritySubs:
                        timestamp = time.time()

                submissionQueue[timestamp] = submission
            
            # someone submitting a MUW
            elif "[submission]" in submission.title.lower():
                pass
            
            # an announcement
            elif "[announcement]" in submission.title.lower():
                pass

            # a help request
            elif "[help]" in submission.title.lower():
                pass
                
            # no valid tag -- remove it
            else:
                submission.add_comment("Your MUW request could not be processed. Please resubmit the request with the following title formats: [Request] /r/SUBREDDIT or [Request] /u/USERNAME")
                submission.remove()
                sys.stderr.write("Submission removed: " + str(submission) + "\n")

def runMUWs():
    """Finds the top requests in /r/MUWs and processes them"""
    
    try:
        fillQueue()
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        sys.stderr.write("Queue error -- restarting\n")
        return

    # work through the submission queue, oldest requests first
    for submission in sorted(submissionQueue):
        try:
            # grab the submission
            submission = submissionQueue[submission]

            # skip the submission if it's been tagged since being queued
            if submission.link_flair_text is not None:
                continue
            
            # find out what kind of request it is
            userRequest = False
            if "u/" in submission.title:
                userRequest = True
            
            # extract the name of the subreddit or user
            title = ""
            splitToken = "r/"
            if userRequest:
                splitToken = "u/"
                
            title = submission.title.split(splitToken)
            title = title[1].split(" ")
            title = title[0].lower()
            title = title.strip("/")
            
            # make sure it's a valid request
            makeMUW = True
            
            try:
                if not userRequest:
                    for s in r.get_subreddit(title).get_top_from_all(limit=1):
                        s.ups
                else:
                    for s in r.get_redditor(title).get_overview(limit=1):
                        s.ups
                        
            except KeyboardInterrupt:
                raise KeyboardInterrupt()
            except:
                # if it's not a valid request, remove the submission and advise the submitter
                makeMUW = False
                submission.add_comment("Your MUW request could not be processed. Please resubmit the request with the following title formats: [Request] /r/SUBREDDIT or [Request] /u/USERNAME")
                submission.remove()
                sys.stderr.write("Submission removed: " + str(submission) + "\n")
            
            if makeMUW:
                # since it's a valid request, gather data on it
                submission.set_flair("Running")
                
                filename = title + ".csv"
                redditLink = title
                
                if userRequest:
                    filename = "user-" + filename
                    redditLink = "/u/" + redditLink
                else:
                    filename = "subreddit-" + filename
                    redditLink = "/r/" + redditLink
                    
                # check if the request has already been parsed
                try:
                    with open("cache/" + filename) as f:
                        sys.stderr.write(redditLink + " has already been mined -- using cache\n")
                        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat("cache/" + filename)
                        
                        daysSinceModified = (datetime.now() - datetime.fromtimestamp(mtime)).days
                        
                        if daysSinceModified >= 7:
                            sys.stderr.write("Cached version is out of date -- re-mining\n")
                            raise IOError("Cached version is out of date")
                        
                except KeyboardInterrupt:
                    raise KeyboardInterrupt()
                except IOError as e:
                    os.system("word_freqs -r rhiever " + redditLink)
                    os.system("mv " + filename + " cache/")
                    
                # place the output in a comment
                headerString = ""
                
                if userRequest:
                    headerString = "Below are the word frequencies for " + redditLink + ". "
                else:
                    headerString = "Below are the word frequencies from the past month for " + redditLink + ". "
                
                headerString += "Place these word frequencies into http://www.wordle.net/advanced and click Go. "
                headerString += "Customize the MUW cloud as you please.\n\n"
                headerString += "Remember to acknowledge this script and /r/MUWs if you post the MUW to a subreddit.\n\n"
                commentString = headerString
                allWords = defaultdict(int)

                with open("cache/" + filename, "r") as infile:
                    for line in infile:
                        if line == "":
                            continue
                        
                        text = line.split(":")
                        count = int(text[-1])
                        word = ""
                        
                        for c in text[:-1]:
                            word += c
                        allWords[word] = count
                        #commentString += line + "\n"
                        
                # if the comment is too long, shorten it to <- 10,000 chars
                # give priority to most-used words
                if True: #len(commentString) > 10000:
                    commentString = headerString.encode("UTF-8")
                    charsLeft = 10000 - len(headerString)
                    
                    for word in sorted(allWords, key=allWords.get, reverse=True):
                        line = "    " + word + ":" + str(allWords[word]) + "\n" #\n
                        charsToPlace = len(line)
                        if charsLeft - charsToPlace < 0:
                            break
                        
                        charsLeft -= charsToPlace
                        commentString += line
                
                try:
                    submission.add_comment(commentString)
                    submission.set_flair("Request Fulfilled")
                except KeyboardInterrupt:
                    raise KeyboardInterrupt()
                except:
                    sys.stderr.write("Error commenting on " + str(submission) + "\n")
        
        except KeyboardInterrupt:
            exit()
        except Exception as e:
            sys.stderr.write(str(e) + "\n")
            sys.stderr.write("Unknown error -- moving to next submission\n")


def main():
    """Processes MUW requests until time runs out"""

    endTime = datetime.now() + timedelta(hours=45)

    r.login(username=sys.argv[2], password=sys.argv[3])

    # run over and over with short sleep breaks
    while datetime.now() < endTime:
        sys.stderr.write("Processing MUW requests\n")
        try:
            runMUWs()
        except KeyboardInterrupt:
            exit()
        except Exception as e:
            sys.stderr.write(str(e) + "\n")
            sys.stderr.write("Unknown error -- restarting\n")

        time.sleep(5)
            
        # sleep for a little bit if there is nothing in the queue
        if not checkQueue():
            sys.stderr.write("No requests to handle -- sleeping\n")
            time.sleep(1800)
            sys.stderr.write("I'm alllliiiivvvveeeee!\n")


if __name__ == '__main__':
    sys.exit(main())
