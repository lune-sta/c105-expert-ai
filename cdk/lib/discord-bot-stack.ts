import * as cdk from 'aws-cdk-lib'
import { Construct } from 'constructs'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as ecs from 'aws-cdk-lib/aws-ecs'

interface DiscordBotStackProps extends cdk.StackProps {
  discordBotToken: string
}

export class DiscordBotStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: DiscordBotStackProps) {
    super(scope, id, props)

    const { accountId, region } = new cdk.ScopedAws(this)

    const vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 1,
    })

    const cluster = new ecs.Cluster(this, 'Cluster', {
      vpc,
    })

    const taskRole = new iam.Role(this, 'TaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    })

    const bedrockInvokeModelPolicy = new iam.ManagedPolicy(
      this,
      'DiscordBotPolicy',
      {
        statements: [
          new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
              'bedrock:InvokeModel',
              'bedrock:Retrieve',
              'bedrock:Rerank',
            ],
            resources: ['*'],
          }),
        ],
      },
    )
    taskRole.addManagedPolicy(bedrockInvokeModelPolicy)

    const taskDefinition = new ecs.FargateTaskDefinition(
      this,
      'TaskDefinition',
      {
        memoryLimitMiB: 1024,
        cpu: 512,
        taskRole,
      },
    )

    taskDefinition.addContainer('BotContainer', {
      image: ecs.ContainerImage.fromAsset('../bot/'),
      logging: new ecs.AwsLogDriver({
        streamPrefix: 'bot',
      }),
      environment: {
        DISCORD_BOT_TOKEN: props?.discordBotToken,
      },
    })

    new ecs.FargateService(this, 'Service', {
      cluster,
      taskDefinition,
    })
  }
}
