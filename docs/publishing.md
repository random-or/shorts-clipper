# Multi-Platform Publishing Engine

Shorts Clipper now includes a generic Multi-Platform Publishing Engine that makes it trivial to distribute clips across multiple platforms autonomously.

## Architecture

The engine uses a Registry-based design:
- `PublishingEngine`: Core orchestrator. Iterates through platforms, attempts authentication, executes publishing, handles retries, and generates a manifest.
- `Publisher`: An abstract base class defining the contract for all platform integrations (`authenticate`, `publish`, `verify`).
- `PublisherRegistry`: A centralized factory where publishers register themselves.

When a clip finishes rendering, the pipeline simply asks the `PublishingEngine` to publish the file to a list of target platforms. The engine operates entirely platform-agnostic.

## Supported Platforms

1. **YouTube Shorts** (`youtube`)
2. **Instagram Reels** (`instagram`)

## Configuration

Publishing is controlled via the `Settings` class and your `.env` file. By default, both platforms are enabled if credentials exist.

```env
# Platforms to publish to (comma-separated)
SHORTS_PUBLISH_PLATFORMS=youtube,instagram

# Instagram Credentials
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

## Authentication Flow

### YouTube
YouTube uses OAuth2. The first time you use it, you must run the Web UI and link your account via the sidebar. This generates a `.cache/shorts-clipper/token.pickle` file containing access and refresh tokens. The Publishing Engine will automatically use and refresh these tokens.

### Instagram
Instagram uses the `instagrapi` library. It performs a direct login using your `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` from `.env`. Upon successful login, the session is dumped to `.cache/shorts-clipper/instagram_session.json` to avoid suspicious login attempts in the future. The engine will reuse this session file.

## How to Add a Future Publisher

Adding a new platform like TikTok or Facebook is simple and requires **zero** changes to the main pipeline.

1. Create a new directory in `shorts_clipper/publishers/` (e.g., `tiktok/`).
2. Create `publisher.py` and implement the `Publisher` interface.
3. Define the `platform_name`, `authenticate()`, `publish()`, and `verify()` methods.
4. Open `shorts_clipper/publishers/__init__.py` and register your new class:
   ```python
   from .tiktok.publisher import TikTokPublisher
   PublisherRegistry.register(TikTokPublisher)
   ```
5. Add `tiktok` to `SHORTS_PUBLISH_PLATFORMS` in your `.env`.

The Publishing Engine will automatically detect and execute your new publisher in the next run.
