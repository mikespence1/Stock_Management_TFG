FROM ruby:3.4-slim
RUN gem install xcodeproj --version 1.28.1 --no-document
WORKDIR /project
ENTRYPOINT ["ruby", "scripts/generate_ios_project.rb"]
