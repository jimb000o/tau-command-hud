# Tau HUD on YouTube: setting up once

The server makes the videos itself (`alerts/yt.py`, see its header). It needs three things that only the channel owner
can give: YouTube access, a voice, and one sign-in. About 20 minutes, once.

## 1. YouTube access (Google Cloud, free)

1. New project: https://console.cloud.google.com/projectcreate (name: `tau-hud-youtube`).
2. Turn on both APIs for that project (press "Enable" on each):
   - https://console.cloud.google.com/apis/library/youtube.googleapis.com
   - https://console.cloud.google.com/apis/library/youtubeanalytics.googleapis.com
3. The sign-in screen: https://console.cloud.google.com/auth/overview → Get started. App name `Tau HUD uploader`,
   audience **External**, your own address as contact. Then under **Audience** press **Publish app** so it says
   **In production**. (In "Testing", Google ends the sign-in after 7 days and the uploads stop.)
4. The client: https://console.cloud.google.com/auth/clients → Create client → type **Desktop app**, name `tau-hud-server`.
   Copy the client ID and the client secret.
5. Put both into the server's `infra/.env` (replace the two values, keep the quotes):

   ```
   ssh root@node.tauhud.com "cd /opt/tau-command-hud/infra && printf '\nYT_CLIENT_ID=%s\nYT_CLIENT_SECRET=%s\n' 'PASTE-CLIENT-ID' 'PASTE-CLIENT-SECRET' >> .env"
   ```

6. Sign in once (the `-t` matters, the command asks you to paste an address):

   ```
   ssh -t root@node.tauhud.com "cd /opt/tau-command-hud && git pull && sh infra/up.sh yt login"
   ```

   It prints a link. Open it, pick the channel **Tau HUD**. Google warns that the app is not verified: Advanced → Go to
   Tau HUD uploader (it is your own app). Allow everything. The browser then shows "127.0.0.1 refused to connect": that
   is right. Copy the whole address from the address line, paste it into the terminal, Enter. It answers with the
   channel's name.

7. Own preview pictures need a phone-verified channel: https://www.youtube.com/verify

## 2. The voice (ElevenLabs)

The videos speak with the owner's own cloned voice (Instant Voice Clone, about one minute of clean recording). The key
is the one the island already uses (`ELEVENLABS_API_KEY` in `infra/.env`).

1. https://elevenlabs.io/app/voice-lab → Add a new voice → Instant Voice Clone → upload the recording.
   If all custom voice slots are taken, delete one you no longer use, or move to a plan with more slots.
2. Copy the new voice's ID (Voices → the voice → ID) and put it into `infra/.env`:

   ```
   ssh root@node.tauhud.com "cd /opt/tau-command-hud/infra && printf '\nYT_VOICE_ID=%s\n' 'PASTE-VOICE-ID' >> .env"
   ```

3. Optional: Rico's short asides. `YT_VOICE_RICO=<his voice id>` the same way; without it his lines are left out.
4. The API key's own limit on ElevenLabs (API keys → the key → credit limit) must leave room: a 2-minute video speaks
   about 1,500 signs. `YT_VOICE_MONTH` (default 60000) stops the service before that.

## 3. The first video

```
ssh root@node.tauhud.com "cd /opt/tau-command-hud && git pull && sh infra/up.sh yt make answer-what-is-tau-net"
```

It is filmed from the live site, cut, and uploaded as a **private** video. The owner's private Telegram gets the link and
the line that makes it public (`up yt send <id>`). From then on the service makes the other answer videos (one every
6 hours), the weekly video on Sunday morning and up to three shorts a week, never while a cruise ship is due.

## What the API cannot do

- The click rate of the preview pictures is not in YouTube's API: YouTube Studio → Analytics → Reach.
- Pinning a comment is not possible through the API: do it by hand in YouTube Studio when wanted.
