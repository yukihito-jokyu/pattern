---
name: ${skill_name}
description: ${summary}
disable-model-invocation: true
---

# ${skill_name}

TODO(forge): このスキルが何をするかを2〜3文で書く（どんな依頼で使うか、終わったときに何ができているか）。

## 役割

${roles}

TODO(forge): 役ごとに、起動するときにプロンプトで渡すものと、返してもらう形を書く。

## 手順

${steps}

TODO(forge): 各手順に、条件で答えが変わる所を「条件 → 答え」で書き足す。サブエージェントに任せる手順には、Agent ツールで起動する名前を書く。

## 人に確かめること

${checkpoints}

## 報告

最後の返答に、次の項目をこの順で書く。

${report}

## してはいけないこと

TODO(forge): このスキルを使うときにしてはいけないことを、理由と一緒に書く。
