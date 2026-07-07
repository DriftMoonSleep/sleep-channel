# Privacy Policy — Driftmoon Sleep Uploader

_Last updated: July 7, 2026_

Driftmoon Sleep Uploader (the "Tool") is a personal, single-user automation
tool that generates original sleep soundscape videos and uploads them to its
owner's own YouTube channel (https://www.youtube.com/@DriftMoonSleep) via
**YouTube API Services**.

## YouTube API Services
The Tool uses YouTube API Services. By using the Tool, its user agrees to be
bound by the [YouTube Terms of Service](https://www.youtube.com/t/terms).
Google's handling of information is described in the
[Google Privacy Policy](https://policies.google.com/privacy).

## Data we access
The Tool uses OAuth 2.0 to access **only the channel owner's own YouTube
account**, exclusively to upload videos and set their thumbnails and
metadata (`videos.insert`, `thumbnails.set`). It does not access, collect,
store, share, or process any data belonging to other YouTube users or any
third parties. It has no users other than its owner.

## Data we store
The only credential stored is the channel owner's OAuth refresh token, kept
encrypted as a GitHub Actions secret. No YouTube API data is stored, cached,
shared, sold, or used for any other purpose. The Tool has no database and
does not use cookies or analytics.

## Data retention and deletion
No API data is retained. To delete the stored credential, the owner can
(a) revoke the Tool's access at any time via
[Google security settings](https://myaccount.google.com/permissions), and
(b) delete the `YT_REFRESH_TOKEN` secret from the repository settings.
Revoking access immediately invalidates the stored token.

## Third parties
No data is shared with any third party. The Tool runs on GitHub Actions
infrastructure solely to execute the generation and upload process.

## Google user data
Use of information received from Google APIs adheres to the
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
including the Limited Use requirements, and to the
[YouTube API Services Terms of Service](https://developers.google.com/youtube/terms/api-services-terms-of-service).

## Contact
driftmoonsleep@gmail.com
