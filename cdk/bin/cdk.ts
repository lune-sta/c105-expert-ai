#!/usr/bin/env node
import 'source-map-support/register'
import * as cdk from 'aws-cdk-lib'
import { SlackBotStack } from '../lib/slack-bot-stack'
import { DiscordBotStack } from '../lib/discord-bot-stack'

const app = new cdk.App()

if (process.env.SLACK_SIGNING_SECRET_DEV && process.env.SLACK_BOT_TOKEN_DEV) {
  new SlackBotStack(app, 'SlackBotDev', {
    env: {
      account: process.env.CDK_DEFAULT_ACCOUNT,
      region: process.env.CDK_DEFAULT_REGION,
    },
    slackSigningSecret: process.env.SLACK_SIGNING_SECRET_DEV,
    slackBotToken: process.env.SLACK_BOT_TOKEN_DEV,
  })
}

if (process.env.SLACK_SIGNING_SECRET_PROD && process.env.SLACK_BOT_TOKEN_PROD) {
  new SlackBotStack(app, 'SlackBotProd', {
    env: {
      account: process.env.CDK_DEFAULT_ACCOUNT,
      region: process.env.CDK_DEFAULT_REGION,
    },
    slackSigningSecret: process.env.SLACK_SIGNING_SECRET_PROD,
    slackBotToken: process.env.SLACK_BOT_TOKEN_PROD,
  })
}

if (process.env.DISCORD_BOT_TOKEN) {
  new DiscordBotStack(app, 'DiscordBotStack', {
    env: {
      account: process.env.CDK_DEFAULT_ACCOUNT,
      region: process.env.CDK_DEFAULT_REGION,
    },
    discordBotToken: process.env.DISCORD_BOT_TOKEN,
  })
}
