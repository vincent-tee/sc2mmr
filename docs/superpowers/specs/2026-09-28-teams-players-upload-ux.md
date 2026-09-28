# Teams, Players and Upload UX: next steps

**Created:** 2026-09-28
**Status:** Approved order; nothing implemented yet except item 0.
**Author:** AI Assistant + User

## Overview

An outside UI review of sc2mmr.vercel.app (2026-09-28) was accepted with small changes. The goal is less
noise and a Teams page built around what happens on game night. Keep the visual personality: orange
accents, avatars, a competitive tone. Follow the Clubhouse style rules in memory (`design-direction-clubhouse`).

## 0. Done this session (as of 2026-09-28)

- Removed the Recent Form, Combat, Hot Streak and Marathon boards. Players keeps only MMR and Win Rate.
- Removed the duplicated win-rate column. Commit `9af1e94`: pushed, **not deployed**. Deploy it first.
  It has no migrations.

## 1. Teams page: balance ranking bug and one balance headline (do first)

**Bug:** `frontend/src/pages/TeamGenerator/BalanceResults.tsx:19` labels option 0 "Fairest". The options
arrive ranked by the balancer's objective, but each shows `match_quality`. So "Fairest 72%" can sit above
"Option 3 73%".

- [ ] Rank the options by the number that is shown. Alternatively, show the number they are actually ranked
  by. Check which is right in `backend/app/services/balancer.py`.
- [ ] Use one headline: "Closely matched · 47% / 53%". Move match quality and the MMR gap into a details line.
- [ ] Explain in one sentence why this split was recommended.

## 2. Teams page: results take focus after Generate

- [ ] After Generate, collapse the player picker to "8 players · Change lineup".
- [ ] Show both teams, the balance headline and the actions together on a laptop screen.
- [ ] Make **Copy teams** the main action. Put alternatives and swap suggestions below it.

## 3. Consistent result wording

- [ ] History badge "WIN?", the match heading "Team 2 won" and the notice "result unconfirmed" become
  **"Inferred win"** everywhere for `result_source = suggested`. The rule behind them (a clear supply lead)
  is right 99.5% of the time, so "unconfirmed" overstates the doubt.
- [ ] Keep "No result" for `unknown`. Keep "Not rated" for `not_rateable`.
- Files: `frontend/src/pages/MatchHistory.tsx` (TeamRoster badge and tooltip),
  `frontend/src/pages/MatchDetail/MatchHeader.tsx` (SuggestedResultNotice).

## 4. Players page and profiles

- [ ] Replace the podium with one sortable table, with small medals for ranks 1–3, and search at the top.
- [ ] Keep recent form as the existing hot/cold badge only. The owner removed the Recent Form board as noise,
  so don't make form prominent again.
- [ ] Profile (`frontend/src/pages/PlayerDetail.tsx`): show rating, trend and recent games first. Collapse
  "How this MMR adds up" (MMRBreakdown).

## 5. Smaller clean-ups

- [ ] Upload: when nothing needs attention, replace the two empty "Needs attention" cards with one line,
  "Everything up to date" (`frontend/src/pages/Upload/NeedsAttention.tsx`).
- [ ] Head to Head: the player picker should list current squad players only, searchable. It currently lists
  many identical 1,833 ratings, which are players with almost no games showing the starting rating.
- [ ] Match history: replace the row of team-size filters with a compact mode selector plus player and date
  filters. Group matches by playing night and use tighter rows.

## 6. Replay-folder button on the Upload page

Owner decision: **a button only.** No timer, no tab-focus checks, no background running.

Design:
- The first click calls `window.showDirectoryPicker({ id: 'sc2-replays' })`. The user picks
  `Documents\StarCraft II\Accounts\<id>\<id>\Replays\Multiplayer`. Store the handle in IndexedDB.
- Later clicks:
  - Check folder access with `queryPermission`, then `requestPermission`. The click counts as the user
    gesture the browser requires.
  - List `.SC2Replay` files and skip names already seen. The seen set lives in IndexedDB.
  - Skip files modified in the last ~10 s, since SC2 may still be writing them.
  - Pass the new `File`s to the Upload page's existing `onDrop` (`frontend/src/pages/UploadReplays.tsx:204`).
    That reuses the queue, progress list, sign-in prompt, retry and query refresh.
- First connect: queue files modified in the last 24 h. Mark older ones as seen so the whole back
  catalogue isn't uploaded.
- Show "N new games added" or "No new games since last time", plus a small "Change folder" link.
- Chrome and Edge only (File System Access API). Hide the button elsewhere; drag-and-drop still works.

Server behaviour, checked 2026-09-28:
- The server rejects squad members' games against strangers with a 400. They fail the "each team has a
  player with > 10 games" check (`backend/app/services/ingestion.py:119`) and are **not** logged to Failed
  uploads.
- The same file is deduplicated by hash.
- Other players' recordings of the same game upload once each. That is useful: a second recording often
  carries the real result when ChrisO's recording ended early (all 11 of the day's unknowns were his).

Cost, measured on 572 local replays: median 216 KB, 90th percentile 357 KB, max 677 KB. Scanning the folder
uses no network. Allow about 2–3 MB per player per game night.

- [ ] `frontend/src/utils/replayFolder.ts`: IndexedDB get/set for the handle and seen set, plus
  `newReplays(dir)`.
- [ ] `frontend/src/pages/Upload/ReplayFolderButton.tsx`: the button, the status line and "Change folder".
- [ ] Wire it into `UploadReplays.tsx` below the dropzone, visible only when `'showDirectoryPicker' in window`.

## 7. Later (after 1–6)

- **Game-night sessions:**
  - Pick tonight's squad once and keep the teams visible between games.
  - Offer Rematch, and Rebalance with an option to avoid repeated teammates.
  - Attach replays to the night.
  - The "avoid repeated teammates" option is a new balancing feature. Validate it against results per the
    house rules.
- **Night recap:** wins, rating movement, closest game and notable performances, shareable. Depends on
  sessions.

## Rollback

Everything here is frontend-only, apart from item 1's possible balancer ordering change. Revert the
commit and redeploy the frontend. There are no database changes.
