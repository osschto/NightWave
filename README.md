# NightWave

NightWave is an application for listening to audiobooks and podcasts.

## API

To use the application, obtain your API credentials from [Podcast Index](https://api.podcastindex.org/).

Create a `.env` file in the root directory of the project using `.env.example` as a template, then insert the API credentials you obtained:

```env
PODCAST_INDEX_KEY=your_api_key
PODCAST_INDEX_SECRET=your_api_secret
```

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running

NightWave can be launched using terminal commands or through Visual Studio Code.

### Using terminal commands

**PC:**
```bash
flet run main.py
```

**Android:**
```bash
flet run main.py --android
```

**iOS:**
```bash
flet run main.py --ios
```

### Using Visual Studio Code

If you are using VS Code, press `Ctrl + Shift + B` to open the list of available tasks.

Select the desired task:

- `Run on PC` — launches the application on your computer.
- `Run on Android` — launches the application on an Android device.
- `Run on iOS` — launches the application on an iOS device.

**Note:** To run the application on Android or iOS, install the Flet app on your mobile device from [Google Play](https://play.google.com/store/apps/details?id=com.appveyor.flet&pcampaignid=web_share) or the [App Store](https://apps.apple.com/de/app/flet/id1624979699?l=en-GB). Your device and development computer must be connected to the same network.

VS Code tasks support hot reload, allowing you to see code changes during development.