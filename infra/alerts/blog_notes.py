"""Sections written by hand for a drafted article (blog.py adds them to the draft the model wrote), and drafts held back
from publishing themselves until the owner has read them.

  NOTES["<article id>"] = {
      "hold": "why it waits",          # never published by itself (auto_publish); up blog publish <id> as always
      "sections": {"en": "## ...", "zh": "## ...", "ja": "## ..."},   # Markdown, put in before the last section
  }

The sections go in before the draft's last section ("What is still open"), in all three languages; the model's own text
is kept beside them (body_model), so changing a note here and `up blog` puts the new text in, never twice.
Only what we saw and can show; nothing that IDNI has not been told yet."""

NOTES: dict[str, dict] = {
    # 14 Nov 2026: no block reached our node after #1569 during the Queen's call; later that afternoon the testnet was
    # restarted and the old chain ended at #1569 (the explorer shows the new chain, so no link to the old block).
    # Kilian asked for what we checked and what we learned; only what we saw.
    "2026-11-14-queen-learnings": {
        "hold": "the blocks section waits for a read: up blog publish 2026-11-14-queen-learnings when it is right",
        "sections": {
            "en": """## What happened to the blocks?

We checked this first, because a ship that slows the chain down would be our mistake to own.

- Up to the Queen's arrival everything looked normal. Blocks 1563 to 1568 reached our node about one a minute from 12:55 UTC on. Block 1569 was made at 13:01:52 UTC, shortly after the Queen arrived at 13:00. Like the blocks before it, it was small and plain: one transfer of 3 AGRS, where each of the three before held one or two transfers, and no rule changes in any of them. By then the Queen had sent only a few payments, all while our node rated the load as calm.
- After block 1569, no new block reached our node. Our node stayed up and kept taking in transfers (21 were waiting when the ship left), but it lost its connection to the rest of the network.
- Later that afternoon the testnet was [restarted](/stats/) from its starting state. The old chain ended at block 1569, so it was the last block of that chain. Balances, rules and history begin again on the new one, and the explorer now shows the new chain, which is why block 1569 is described here in words.
- Why the old chain ended there is for the IDNI team to say. We do not know whether it stopped on its own or was ended for the restart.
- [On 7 November](/blog/?p=2026-11-07-queen-learnings) the same ship sent more than 400 payments in 90 minutes, and our node kept receiving blocks the whole time.
- The ship did what it is built to do. When the newest block on our node was more than ten minutes old with payments waiting, she left at once instead of sending more into a queue that was not moving.

Nothing we found points to the ship's load, though we cannot rule it out. The last block looks ordinary. We will write more once the IDNI team has seen what we found.

## What we learned

- The brake is right. It made the call short, but a test ship should not keep sending while its node gets no new blocks. It stays as it is.
- Our ship only sees our own node. "No new blocks here" can be a stalled chain, a lost connection or a chain that is about to start over, and the ship, like the first draft of this article, called it a stall. Next time we check our node's connection before we name it.
- Load is not the only thing to watch. This came on a quiet chain, so we also look at what a node does with each new block, not only at how many payments go out.
- A short call is a result too. We show it as it was: 12 of 90 minutes, in amber, not in green.""",
            "zh": """## 区块发生了什么？

我们首先查的就是这一点，因为如果是船拖慢了链，那就是我们的错，应由我们承担。

- 在 Queen 到达之前，一切看起来都正常。从 UTC 12:55 起，第 1563 到 1568 号区块大约每分钟一个到达我们的节点。第 1569 号区块在 UTC 13:01:52 产生，那时 Queen 13:00 刚到不久。和之前的区块一样，它很小也很普通：只有一笔 3 AGRS 的转账，之前三个区块各有一到两笔转账，其中都没有规则变更。到那时 Queen 只发出了很少几笔付款，我们的节点当时把负载评为平静。
- 第 1569 号区块之后，再没有新区块到达我们的节点。我们的节点一直在线，并继续接收转账（船离开时有 21 笔在等待），但它与网络其余部分失去了连接。
- 当天下午晚些时候，测试网从初始状态[重新启动](/stats/)。旧链在第 1569 号区块结束，所以它就是那条链的最后一个区块。余额、规则和历史在新链上重新开始，浏览器现在显示的是新链，所以我们在这里用文字描述第 1569 号区块。
- 旧链为什么在那里结束，应由 IDNI 团队来说明。我们不知道它是自己停下的，还是为了重启而结束的。
- [11 月 7 日](/blog/?p=2026-11-07-queen-learnings)，同一艘船在 90 分钟里发出了 400 多笔付款，我们的节点在整个过程中一直收到新区块。
- 船做了它被设计要做的事：当我们节点上最新的区块已超过十分钟、还有付款在等待时，它立刻离开，而不是继续往一个不动的队列里发送。

我们没有找到任何指向船的负载的迹象，但也不能排除。最后一个区块看起来很普通。等 IDNI 团队看过我们的发现后，我们会再写。

## 我们学到了什么

- 刹车是对的。它让这次停靠变得很短，但当节点收不到新区块时，测试船不应该继续发送。它保持不变。
- 我们的船只能看到我们自己的节点。“这里没有新区块”可能是链停了、连接断了，或者链即将重新开始；船和这篇文章的初稿都把它叫作停顿。下次我们会先检查节点的连接，再下结论。
- 负载不是唯一要看的东西。这次发生在安静的链上，所以我们现在也看节点如何处理每一个新区块，而不只看发出了多少付款。
- 短暂的停靠也是一个结果。我们如实展示：90 分钟里只有 12 分钟，用琥珀色，而不是绿色。""",
            "ja": """## ブロックに何が起きたのか？

まずこれを確かめました。船がチェーンを遅くしたのなら、それは私たちの責任だからです。

- Queen が着くまでは、すべて普段どおりに見えました。UTC 12:55 から、ブロック 1563 から 1568 がほぼ 1 分に 1 つずつ私たちのノードに届きました。ブロック 1569 が作られたのは UTC 13:01:52、Queen が 13:00 に着いて間もない頃です。それまでのブロックと同じく小さくごく普通で、3 AGRS の送金が 1 件だけでした。その前の 3 つのブロックもそれぞれ送金 1〜2 件で、ルールの変更はどれにもありません。その時点で Queen が送った支払いはわずかで、ノードは負荷を「落ち着いている」と判定していました。
- ブロック 1569 の後、新しいブロックは私たちのノードに届きませんでした。ノードは動き続け、送金を受け付けていました（船が去ったとき 21 件が待っていました）が、ネットワークの他の部分とのつながりを失いました。
- その日の午後、テストネットは初期状態から[再起動](/stats/)されました。古いチェーンはブロック 1569 で終わったので、これがそのチェーンの最後のブロックです。残高、ルール、履歴は新しいチェーンで最初から始まり、エクスプローラーは今は新しいチェーンを表示しています。そのため、ブロック 1569 はここで言葉で説明しています。
- 古いチェーンがなぜそこで終わったのかは、IDNI チームが説明することです。自然に止まったのか、再起動のために終えられたのかは、私たちにはわかりません。
- [11 月 7 日](/blog/?p=2026-11-07-queen-learnings)、同じ船は 90 分間で 400 件以上の支払いを送り、その間私たちのノードはずっと新しいブロックを受け取っていました。
- 船は設計どおりに動きました。ノード上の最新ブロックが 10 分以上前のもので支払いが待っているとき、動かない列にさらに送らず、すぐに出航しました。

船の負荷を示すものは見つかっていませんが、否定もできません。最後のブロックはごく普通です。IDNI チームが私たちの調べた内容を見た後で、また書きます。

## わかったこと

- ブレーキは正しい判断でした。寄港は短くなりましたが、ノードに新しいブロックが来ないうちは、テストの船は送り続けるべきではありません。このままにします。
- 船が見ているのは私たちのノードだけです。「ここに新しいブロックが来ない」は、チェーンの停止、接続の切断、あるいはまもなく始まる再起動のどれでもありえます。船もこの記事の最初の下書きも、それを停止と呼びました。次からは、名前をつける前にノードの接続を確かめます。
- 見るべきなのは負荷だけではありません。今回は静かなチェーンで起きたので、送った支払いの数だけでなく、ノードが新しいブロックごとに何をしているかも見ています。
- 短い寄港も結果のひとつです。そのまま見せます。90 分のうち 12 分、緑ではなく琥珀色で。""",
        },
    },
}
