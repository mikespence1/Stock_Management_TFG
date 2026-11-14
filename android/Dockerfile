FROM eclipse-temurin:21-jdk-jammy AS tools
ARG ACCEPT_ANDROID_SDK_LICENSES=no
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=/opt/gradle/gradle-8.13/bin:/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/build-tools/36.0.0:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ca-certificates && rm -rf /var/lib/apt/lists/*
RUN curl --fail --location --retry 3 https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip -o /tmp/sdk.zip \
    && echo '4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583  /tmp/sdk.zip' | sha256sum -c - \
    && mkdir -p /opt/android-sdk/cmdline-tools && unzip -q /tmp/sdk.zip -d /opt/android-sdk/cmdline-tools \
    && mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest && rm /tmp/sdk.zip
RUN test "$ACCEPT_ANDROID_SDK_LICENSES" = yes \
    && yes | sdkmanager --licenses >/dev/null \
    && sdkmanager 'platforms;android-36' 'build-tools;36.0.0'
RUN curl --fail --location --retry 3 https://services.gradle.org/distributions/gradle-8.13-bin.zip -o /tmp/gradle.zip \
    && echo '20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78  /tmp/gradle.zip' | sha256sum -c - \
    && mkdir -p /opt/gradle && unzip -q /tmp/gradle.zip -d /opt/gradle && rm /tmp/gradle.zip

FROM tools AS build
WORKDIR /project
COPY . .
RUN --mount=type=cache,id=givingflow-android-signing,target=/root/.android \
    --mount=type=cache,id=givingflow-gradle,target=/root/.gradle \
    gradle --no-daemon --console=plain testDebugUnitTest assembleDebug \
    && apksigner verify --verbose app/build/outputs/apk/debug/app-debug.apk \
    && mkdir /out && cp app/build/outputs/apk/debug/app-debug.apk /out/GivingFlow-debug.apk \
    && sha256sum /out/GivingFlow-debug.apk > /out/GivingFlow-debug.apk.sha256

FROM scratch AS artifact
COPY --from=build /out/ /
