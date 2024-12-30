C105のらぼちく本で `精度の高いRAGを組んでプログラミングお手伝いAIを作る` に使用したサンプルコードです。

文中ではクエリフィルターの作成を自前で実装していましたが、[自動でクエリフィルターを生成する機能](https://dev.classmethod.jp/articles/new-feature-amazon-bedrock-knowledge-bases-starts-providing-auto-generated-query-filters-awsreinvent/
)が最近追加されていたのでそちらを使用しました。 何か実装する前には新機能や既存の機能を確認しておきましょう（1敗）

フォルダ構成：
```
.
├── README.md ... このファイル
├── bot ... RAGや回答生成の実装、SlackやDiscordのBotのコード
├── cdk ... BotをAWSにデプロイするコード ※Knowledge Base は含まれません
├── crawler ... ファイルを集める仕組み
└── requirements.txt ... 依存ライブラリ
```
