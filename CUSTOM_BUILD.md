# Custom Jellyfin 12 build

This branch starts at official Jellyfin v12 (`6c073e19ddf604b2369c638716164fdab4c952dc`)
and applies five database fixes submitted upstream:

- UserData reattachment ([#17891](https://github.com/jellyfin/jellyfin/pull/17891)): `42b507efe1ccdf530714e46842e1e1131559c324`.
- Orphan ItemValues cleanup ([#17892](https://github.com/jellyfin/jellyfin/pull/17892)): `2d4850107a4ee60ebbfde662278eb42e45d11c27`.
- Orphan people cleanup ([#17897](https://github.com/jellyfin/jellyfin/pull/17897)): `544b893886f1c623295fa04ccf128cde7f6a6ae6`.
- Atomic database restore ([#17899](https://github.com/jellyfin/jellyfin/pull/17899)): `82e377d215f0928edb395d3c12474237437ed830`.
- Restore IDs and provider completion ([#17901](https://github.com/jellyfin/jellyfin/pull/17901)): `f267bc064173b7344c18fc288591e4d0972c5ea5`.

The restore follow-ups `f405492dd3c9a358cc8e02cf6715eeb2dc3b15cd` and
`46639d35ffe98b72a280ada4c436aa401728e4fb` are also included. Assembly versions
remain `12.0.0`; custom release and image tags identify these additions.

## Docker image

The image uses the pinned official v12 image for its web client, FFmpeg and
runtime dependencies. The entire server payload is replaced with a
self-contained build of this branch. PostgreSQL support is packaged separately
in the matching plugin image.

The image is:

```text
ghcr.io/nintwentydo/jellyfin:12.0.0-nintwentydo.1
```

Pushing `release/12-custom` runs the full Debug suite and native AMD64/ARM64
image checks without publishing. After reviewing a passing branch build, tag
the same commit `v12.0.0-nintwentydo.1` to run the checks and publish to GHCR.
Later releases increment the final number. Existing workflow runs can be rerun
from the Actions page.

The shared version and commit tags are published only after both architecture
checks pass. No Docker Hub credentials or publication are needed. After the
first publication, make the GHCR package public, or grant the plugin repository's
Actions access to pull it. A GitHub release can link to the image and source tag;
creating the release does not bump Jellyfin's assembly version on this fork.

## Local validation

On a native Linux AMD64 machine with .NET 10 and Docker:

```sh
dotnet test Jellyfin.sln --configuration Debug
dotnet publish Jellyfin.Server/Jellyfin.Server.csproj --configuration Release \
  --runtime linux-x64 --self-contained true --output docker/server \
  -p:DebugSymbols=false -p:DebugType=none
docker build -f docker/Dockerfile -t jellyfin-v12-custom:review \
  --build-arg IMAGE_VERSION=12.0.0-nintwentydo-dev docker
python3 docker/smoke-test.py jellyfin-v12-custom:review amd64
```

Use `linux-arm64` and `arm64` on a native Linux ARM64 machine. The smoke check
uses temporary configuration and verifies the compiled payload, startup,
authentication, web client, FFmpeg and account persistence after restart.

Database plugins are distributed separately and are not part of the core
image validation.
