#! /usr/bin/python3
import requests
from requests.auth import HTTPBasicAuth
import json
import datetime
import argparse

# tasks details: https://onedior.atlassian.net/browse/ONE-6650
with open("config.json") as config_file:
    config = json.load(config_file)

jiraUserName = config["JIRA_USERNAME"]
jiraApiToken = config["JIRA_API_TOKEN"]
jiraApiHost = "https://onedior.atlassian.net/rest/api/3/"
confluenceApiHost = (
    "https://onedior.atlassian.net/wiki/rest/calendar-services/1.0/calendar/"
)
timePerIssue = config["timePerDay"]


def get_cli_args():
    parser = argparse.ArgumentParser(description="fill in the CRA for the current week")
    parser.add_argument(
        "--force",
        help="ignore already contributed day and off days check",
        action="store_true",
    )
    parser.add_argument(
        "--setup",
        help="paste the script required for crontab setup",
        action="store_true",
    )
    parser.add_argument(
        "--month",
        help="fill in a month instead of just the current week",
        action="store_true",
    )
    parser.add_argument(
        "--yes",
        help="no user input required (assume yes)",
        action="store_true",
    )
    parser.add_argument(
        "--dry-run",
        help="Do not add the workload",
        action="store_true",
    )
    return parser.parse_args()


def yes_or_no(question):
    reply = str(input(f"{question} (y/n): ")).lower().strip()
    if reply[0] == "y":
        return True
    if reply[0] == "n":
        return False
    else:
        return yes_or_no("Uhhhh... please enter ")


def get_store_days_contributed():
    days_contributed = []
    try:
        with open("store.json", "r") as store_file:
            days_contributed = json.load(store_file)
    except:
        pass
    return days_contributed


def remove_duplicates(list_of_values):
    return list(dict.fromkeys(list_of_values))


def set_store_days_contributed(new_days):
    days_contributed = get_store_days_contributed()
    with open("store.json", "w") as store_file:
        days_contributed.extend(new_days)
        json.dump(remove_duplicates(days_contributed), store_file)


def day_with_week(day, days_contributed):
    return (day, day.strftime("%Y-%m-%d"), str(day) in days_contributed)


def getDays(useMonth=False):
    days_contributed = get_store_days_contributed()
    days = getDaysOfThisMonth() if useMonth else getDaysOfThisWeek()
    return tuple(map(lambda day: day_with_week(day, days_contributed), days))


def getDaysOfThisWeek():
    theday = datetime.datetime.today()
    weekday = theday.isoweekday()
    start = theday - datetime.timedelta(days=weekday - 1)
    return [start + datetime.timedelta(days=d) for d in range(5)]


def getDaysOfThisMonth():
    theday = datetime.datetime.today()
    start = datetime.datetime(theday.year, theday.month, 1)
    end = datetime.datetime(
        theday.year if theday.month < 12 else theday.year + 1,
        theday.month + 1 if theday.month < 12 else 1,
        1,
    )
    nbOfDay = (end - start).days
    dates = [start + datetime.timedelta(days=d) for d in range(nbOfDay)]
    return filter(lambda x: x.isoweekday() < 6, dates)


def addWorklogForOneIssueOneDay(
    issueNumber, startDate: datetime, timeSpent, dry_run=False
):
    if dry_run:
        print("Success ✅")
        return

    auth = HTTPBasicAuth(jiraUserName, jiraApiToken)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = json.dumps(
        {
            "timeSpentSeconds": timeSpent * 3600,
            "started": f"{startDate}T09:30:00.000+0000",
        }
    )
    # doc: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-worklogs/
    response = requests.request(
        "POST",
        f"{jiraApiHost}issue/{issueNumber}/worklog",
        data=payload,
        headers=headers,
        auth=auth,
    )

    if response.status_code == 201:
        print("Success ✅")
    else:
        print("Something went wrong, you have to check on Jira... ❌")
    if not response.ok:
        raise RuntimeError(response.text)


def day_in_contributed_(days_contributed, week_of_day):
    return week_of_day in days_contributed


def addWorkloadForAllDays(days_to_contribute, dry_run=False):
    for x in days_to_contribute:
        day = x[1]
        for issue in timePerIssue:
            if timePerIssue[issue] != 0:
                print(f"Day {day}: Adding {timePerIssue[issue]} hours to issue {issue}")
                addWorklogForOneIssueOneDay(issue, day, timePerIssue[issue], dry_run)

    if not dry_run:
        set_store_days_contributed(
            map(
                lambda x: x[1],
                days_to_contribute,
            )
        )


def map_calendar_value(value):
    return {
        "end": datetime.datetime.strptime(value["end"][:10], "%Y-%m-%d"),
        "start": datetime.datetime.strptime(value["start"][:10], "%Y-%m-%d"),
        "id": value["invitees"][0]["id"].replace("ari:cloud:identity::user/", ""),
        "title": value["title"],
    }


def format_date_for_calendar_api(date_to_format):
    return (date_to_format).strftime("%Y-%m-%d") + "T00%3A00%3A00Z"


def get_user_id():
    auth = HTTPBasicAuth(jiraUserName, jiraApiToken)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    # doc: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-myself/#api-group-myself
    response = requests.request(
        "GET",
        f"{jiraApiHost}myself",
        headers=headers,
        auth=auth,
    )
    if not response.ok:
        raise RuntimeError(response.text)

    return response.json()["accountId"]


def get_off_days_for_user(days_to_contribute):
    user_id = get_user_id()
    off_days = get_off_days(tuple(map(lambda x: x[0], days_to_contribute)))
    return tuple(filter(lambda x: x["id"] == user_id, off_days))


def get_off_days(dates):
    print("Getting off days")
    auth = HTTPBasicAuth(jiraUserName, jiraApiToken)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    # experimental / undocumented api https://community.atlassian.com/t5/Team-Calendars-for-Confluence/Confluence-REST-API-to-read-Calendar-events/qaq-p/1017982
    start = format_date_for_calendar_api(dates[0])
    end = format_date_for_calendar_api(dates[-1] + datetime.timedelta(days=1))
    response = requests.request(
        "GET",
        f"{confluenceApiHost}events.json?subCalendarId=3f864e32-5251-4bb6-8f33-01060102f310&start={start}&end={end}",
        headers=headers,
        auth=auth,
    )
    if not response.ok:
        raise RuntimeError(response.text)

    return tuple(map(lambda x: map_calendar_value(x), response.json()["events"]))


def print_cron_tab_setup():
    print(
        f"To setup this script as a cron, setup your config.json with the common workload, then open your crontab (run 'crontab -e') and paste the following, updating the absolute path to this folder:"
        + "\n\n0 10 * * 1-5 cd /path/to/timetracking-enhanced/folder;./timetracking.py --yes"
    )


def filter_days_contributed_and_leaves(days_to_contribute):
    off_days = get_off_days_for_user(days_to_contribute)
    return tuple(
        filter(
            lambda x: x[2] == False
            and all(
                x[0] < off_day["start"] or x[0] > off_day["end"] for off_day in off_days
            ),
            days_to_contribute,
        )
    )


def main():
    args = get_cli_args()
    if args.setup:
        print_cron_tab_setup()
        exit(0)
    days_to_contribute = getDays(args.month)
    days_ignoring_contributed = (
        days_to_contribute
        if args.force
        else filter_days_contributed_and_leaves(days_to_contribute)
    )
    if len(days_ignoring_contributed) == 0:
        print(
            "all days have already been contributed, launch with '--force' to ignore the check"
        )
        exit(0)
    print("💡 This will add predefined worklog on the following days:")
    print(" ".join(map(lambda x: x[1], days_ignoring_contributed)))

    if not args.yes and not yes_or_no("Do you confirm ?"):
        print("Ok aborting 😈")
        exit(0)

    addWorkloadForAllDays(days_ignoring_contributed, args.dry_run)


if __name__ == "__main__":
    main()
