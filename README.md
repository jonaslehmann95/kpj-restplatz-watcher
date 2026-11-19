# KPJ Restplatz watcher

Checks [MedUni Wien's KPJ page](https://kinder-jugendheilkunde.meduniwien.ac.at/studium-aus-und-weiterbildung/klinisch-praktisches-jahr-kpj/)
every 20 minutes using GitHub Actions (scheduled runs can be delayed by GitHub).

**Subscribe:** install the ntfy app, select the default `https://ntfy.sh` server,
and subscribe to **`kpj-restplatz-1ec30273`** (or open
<https://ntfy.sh/kpj-restplatz-1ec30273>). Enable notifications for the topic.
The topic is public: anyone knowing its name can read or publish messages.

After merging to `main`, the **Watch KPJ places** workflow runs automatically.
Use **Actions → Watch KPJ places → Run workflow** with `test_notification`
checked to send a test message without checking availability or changing state.
The watcher always runs the code and state from `main`.

Positive counts send a high-priority notification with a link to the page on
change and then at most once every four hours while unchanged. Zero is silent.
Fetch and parse failures send normal-priority alerts once per failure kind;
successful checks reset failure deduplication. Recovery to a positive count
alerts immediately. Failed ntfy sends fail the workflow without advancing state,
so the next run retries. Check Actions for notification or state-push failures.

`state.json` is committed by the workflow to persist deduplication. Actions needs
write access to repository contents, and branch rules must allow the bot to push
state updates to `main`. Serialized watcher runs prevent concurrent state writes.
GitHub may disable schedules in inactive public repositories after 60 days;
re-enable the workflow in Actions if needed.

Local use (Python 3.10+, standard library only):

```sh
python3 -m unittest discover -s tests -v
python3 watcher.py --dry-run  # live fetch; no notification or state write
python3 watcher.py --test-notification  # sends a real test message
```

Parser fixture: `tests/fixtures/kpj.html`, captured from the live page on
2026-11-19 (reported count: 0). Tests run on pull requests and branch pushes.
