import * as cdk from 'aws-cdk-lib'
import { Construct } from 'constructs'
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb'
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as python from '@aws-cdk/aws-lambda-python-alpha'
import * as iam from 'aws-cdk-lib/aws-iam'
import { HttpApi } from 'aws-cdk-lib/aws-apigatewayv2'
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations'

interface SlackBotStackProps extends cdk.StackProps {
  slackSigningSecret: string
  slackBotToken: string
}

export class SlackBotStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: SlackBotStackProps) {
    super(scope, id, props)

    const historyTable = new dynamodb.Table(this, 'HistoryTable', {
      partitionKey: {
        name: 'ch_user',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'timestamp',
        type: dynamodb.AttributeType.NUMBER,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    })

    const handler = new python.PythonFunction(this, 'Handler', {
      entry: '../bot',
      index: 'slack_bot.py',
      handler: 'handler',
      runtime: lambda.Runtime.PYTHON_3_12,
      memorySize: 1024,
      timeout: cdk.Duration.seconds(60),
      environment: {
        POWERTOOLS_SERVICE_NAME: 'slack-bot',
        HISTORY_TABLE_NAME: historyTable.tableName,
        SLACK_SIGNING_SECRET: props.slackSigningSecret,
        SLACK_BOT_TOKEN: props.slackBotToken,
      },
    })

    historyTable.grantReadWriteData(handler)

    const bedrockInvokeModelPolicy = new iam.ManagedPolicy(
      this,
      'SlackBotPolicy',
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
    handler.role?.addManagedPolicy(bedrockInvokeModelPolicy)

    const api = new HttpApi(this, 'Api', {
      description: 'Slack bolt app',
      defaultIntegration: new HttpLambdaIntegration('Integration', handler),
    })

    new cdk.CfnOutput(this, 'EndpointUrl', { value: api.apiEndpoint })
  }
}
