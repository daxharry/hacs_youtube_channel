# YouTube Channel Latest

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant integration that tracks the latest videos from one or more YouTube channels using their public RSS feeds — **no API key required**.

## Features

- Monitor multiple YouTube channels simultaneously
- Add channels by **handle** (`@MrBeast`) or **channel ID** (`UCxxxxxx`)
- **Individual sensor per video slot** — each video and each Short is its own HA entity
- **4 info sensors per channel** — channel URL, handle, channel ID, RSS URL
- **Cross-channel Latest feed** — auto-created, aggregates all channels sorted by date
- Last refresh timestamp and status sensor per channel
- Option to exclude Shorts
- No API key required — uses YouTube RSS feeds

## Sensors created per channel

When you add a channel entry (e.g. `@MrBeast`), the following sensors are created:

| Entity | Description |
|---|---|
| `sensor.youtube_mrbeast_last_refresh` | Timestamp of last successful fetch |
| `sensor.youtube_mrbeast_status` | `ok` or `error`, with video/short counts as attributes |
| `sensor.youtube_mrbeast_channel_url` | Link to the channel (`https://www.youtube.com/channel/UCxxx`) |
| `sensor.youtube_mrbeast_channel_handle` | Handle of the channel (e.g. `@MrBeast`) |
| `sensor.youtube_mrbeast_channel_id` | YouTube channel ID (e.g. `UCX6OQ3DkcsbYNE6lgYDiY5Q`) |
| `sensor.youtube_mrbeast_rss_url` | RSS feed URL used to fetch videos |
| `sensor.youtube_mrbeast_video_01` | Latest regular video |
| `sensor.youtube_mrbeast_video_02` | 2nd latest regular video |
| … up to `video_N` | … |
| `sensor.youtube_mrbeast_short_01` | Latest Short |
| … up to `short_N` | … |

Each video/short sensor:
- **State** = video title
- **Attributes**: `url`, `thumbnail`, `description`, `published`, `updated`, `video_id`

## YouTube Latest feed

A **YouTube Latest** entry is created **automatically** the first time you add a channel. It aggregates all videos across all configured channels, sorted by publication date.

| Entity | Description |
|---|---|
| `sensor.youtube_latest_last_refresh` | Timestamp of last refresh |
| `sensor.youtube_latest_status` | `ok` or `error`, with total video count |
| `sensor.youtube_latest_video_01` | Most recent video across all channels |
| `sensor.youtube_latest_video_02` | 2nd most recent |
| … up to `video_N` | … |

Each Latest video sensor:
- **State** = `@ChannelName : Video title`
- **Attributes**: `channel_name`, `url`, `thumbnail`, `description`, `published`, `updated`, `video_id`, `is_short`

## Installation via HACS

1. Open **HACS** in Home Assistant.
2. Go to **Integrations** → three-dot menu → **Custom repositories**.
3. Add `https://github.com/daxharry/youtube_channel_latest` as an **Integration**.
4. Search for **YouTube Channel Latest** and install it.
5. Restart Home Assistant.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **YouTube Channel Latest**.
3. Enter one or more channel handles/IDs (comma or newline separated), set the max number of videos and whether to exclude Shorts.
4. A **YouTube Latest** entry is created automatically — no extra step needed.
5. Repeat to add more channels.

Options can be updated at any time via the integration's **Configure** button.

## Channel input formats

Both formats are accepted:

| Format | Example |
|---|---|
| Handle | `@MrBeast` |
| Channel ID | `UCX6OQ3DkcsbYNE6lgYDiY5Q` |

Multiple channels can be entered separated by commas or newlines.

## Use in Lovelace

### Markdown card — last 10 videos table

```yaml
type: markdown
content: |
  | Chaîne | Titre | Publiée le |
  |---|---|---|
  {% for s in ['sensor.youtube_latest_video_01','sensor.youtube_latest_video_02','sensor.youtube_latest_video_03','sensor.youtube_latest_video_04','sensor.youtube_latest_video_05','sensor.youtube_latest_video_06','sensor.youtube_latest_video_07','sensor.youtube_latest_video_08','sensor.youtube_latest_video_09','sensor.youtube_latest_video_10'] -%}
  {%- set e = states[s] -%}
  {%- if e and e.state not in ['unavailable','unknown'] -%}
  {%- set title = e.state.split(' : ', 1)[1] if ' : ' in e.state else e.state -%}
  | {{ e.attributes.channel_name }} | [{{ title }}]({{ e.attributes.url }}) | {{ as_timestamp(e.attributes.published) | timestamp_custom('%d %b %Y') }} |
  {% endif -%}
  {%- endfor %}
```

### Show thumbnail of latest video

```yaml
type: picture-entity
entity: sensor.youtube_mrbeast_video_01
attribute: thumbnail
```

### Automation — notify on new video from any channel

```yaml
trigger:
  - platform: state
    entity_id: sensor.youtube_latest_video_01
action:
  - service: notify.mobile_app
    data:
      title: "New video!"
      message: "{{ states('sensor.youtube_latest_video_01') }}"
      data:
        url: "{{ state_attr('sensor.youtube_latest_video_01', 'url') }}"
```

## Update interval

Videos are refreshed every **60 minutes**.

## License

MIT
