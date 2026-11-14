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
    # 14 Nov 2026: no block reached our node after #1569 during the Queen's call (our node lost its peer; whether the
    # testnet itself stopped is not known). Kilian asked for what we checked and what we learned; only what we saw.
    "2026-11-14-queen-learnings": {
        "hold": "the blocks section waits for a read: up blog publish 2026-11-14-queen-learnings when it is right",
        "sections": {
            "en": """## What happened to the blocks?

We checked this first, because a ship that slows the chain down would be our mistake to own.

- Up to the Queen's arrival everything looked normal. Blocks 1563 to 1568 reached our node about one a minute from 12:55 UTC on. The last one, [block 1569](https://tauhud.com/explorer/?b=1569), was made at 13:01:52 UTC, shortly after the Queen arrived at 13:00. Like the blocks before it, it was small and plain: one transfer of 3 AGRS, where each of the three before held one or two transfers, and no rule changes in any of them. By then the Queen had sent only a few payments, all while our node rated the load as calm.
- After block 1569, no new block reached our node. Our node stayed up and kept taking in transfers (21 were waiting when the ship left), but it lost its connection to the rest of the network: the node it gets its blocks from no longer completed the connection. At 15:00 UTC it still had no newer block.
- So we do not know yet whether the testnet itself stopped, or whether it went on and only our node was cut off.
- [On 7 November](/blog/?p=2026-11-07-queen-learnings) the same ship sent more than 400 payments in 90 minutes, and our node kept receiving blocks the whole time.
- The ship did what it is built to do. When the newest block on our node was more than ten minutes old with payments waiting, she left at once instead of sending more into a queue that was not moving.

Nothing we found points to the ship's load, though we cannot rule it out yet. The last block looks ordinary. What happened after it is still being checked, and we will write it up once the IDNI team has seen what we found.

## What we learned

- The brake is right. It made the call short, but a test ship should not keep sending while its node gets no new blocks. It stays as it is.
- "No new blocks on our node" is not the same as "the testnet stopped". Our ship, and the first draft of this article, read one as the other. Next time we check our node's connection to the network before we call it a stall.
- Load is not the only thing to watch. This came on a quiet chain, so we also look at what a node does with each new block, not only at how many payments go out.
- A short call is a result too. We show it as it was: 12 of 90 minutes, in amber, not in green.""",
            "zh": """## 区块发生了什么？

我们首先查的就是这一点，因为如果是船拖慢了链，那就是我们的错，应由我们承担。

- 在 Queen 到达之前，一切看起来都正常。从 UTC 12:55 起，第 1563 到 1568 号区块大约每分钟一个到达我们的节点。最后一个是[第 1569 号区块](https://tauhud.com/explorer/?b=1569)，在 UTC 13:01:52 产生，那时 Queen 13:00 刚到不久。和之前的区块一样，它很小也很普通：只有一笔 3 AGRS 的转账，之前三个区块各有一到两笔转账，其中都没有规则变更。到那时 Queen 只发出了很少几笔付款，我们的节点当时把负载评为平静。
- 第 1569 号区块之后，再没有新区块到达我们的节点。我们的节点一直在线，并继续接收转账（船离开时有 21 笔在等待），但它与网络其余部分失去了连接：它获取区块的那个节点不再完成连接。到 UTC 15:00，它仍没有更新的区块。
- 所以我们还不知道，是测试网本身停了，还是测试网仍在运行、只是我们的节点被断开了。
- [11 月 7 日](/blog/?p=2026-11-07-queen-learnings)，同一艘船在 90 分钟里发出了 400 多笔付款，我们的节点在整个过程中一直收到新区块。
- 船做了它被设计要做的事：当我们节点上最新的区块已超过十分钟、还有付款在等待时，它立刻离开，而不是继续往一个不动的队列里发送。

我们没有找到任何指向船的负载的迹象，但目前也不能完全排除。最后一个区块看起来很普通。之后发生了什么仍在核查中；等 IDNI 团队看过我们的发现后，我们再写出来。

## 我们学到了什么

- 刹车是对的。它让这次停靠变得很短，但当节点收不到新区块时，测试船不应该继续发送。它保持不变。
- “我们的节点没有新区块”不等于“测试网停了”。我们的船和这篇文章的初稿都把前者当成了后者。下次我们会先检查节点与网络的连接，再说是停顿。
- 负载不是唯一要看的东西。这次发生在安静的链上，所以我们现在也看节点如何处理每一个新区块，而不只看发出了多少付款。
- 短暂的停靠也是一个结果。我们如实展示：90 分钟里只有 12 分钟，用琥珀色，而不是绿色。""",
            "ja": """## ブロックに何が起きたのか？

まずこれを確かめました。船がチェーンを遅くしたのなら、それは私たちの責任だからです。

- Queen が着くまでは、すべて普段どおりに見えました。UTC 12:55 から、ブロック 1563 から 1568 がほぼ 1 分に 1 つずつ私たちのノードに届きました。最後の[ブロック 1569](https://tauhud.com/explorer/?b=1569) が作られたのは UTC 13:01:52、Queen が 13:00 に着いて間もない頃です。それまでのブロックと同じく小さくごく普通で、3 AGRS の送金が 1 件だけでした。その前の 3 つのブロックもそれぞれ送金 1〜2 件で、ルールの変更はどれにもありません。その時点で Queen が送った支払いはわずかで、ノードは負荷を「落ち着いている」と判定していました。
- ブロック 1569 の後、新しいブロックは私たちのノードに届きませんでした。ノードは動き続け、送金を受け付けていました（船が去ったとき 21 件が待っていました）が、ネットワークの他の部分とのつながりを失いました。ブロックを受け取っている相手のノードとの接続が成立しなくなったのです。UTC 15:00 の時点でも、新しいブロックはありませんでした。
- そのため、テストネット自体が止まったのか、それともテストネットは動き続けていて私たちのノードだけが切り離されたのかは、まだわかりません。
- [11 月 7 日](/blog/?p=2026-11-07-queen-learnings)、同じ船は 90 分間で 400 件以上の支払いを送り、その間私たちのノードはずっと新しいブロックを受け取っていました。
- 船は設計どおりに動きました。ノード上の最新ブロックが 10 分以上前のもので支払いが待っているとき、動かない列にさらに送らず、すぐに出航しました。

船の負荷を示すものは見つかっていませんが、まだ否定もできません。最後のブロックはごく普通です。その後に何が起きたのかはまだ調べています。IDNI チームが私たちの調べた内容を見た後で、記事にします。

## わかったこと

- ブレーキは正しい判断でした。寄港は短くなりましたが、ノードに新しいブロックが来ないうちは、テストの船は送り続けるべきではありません。このままにします。
- 「私たちのノードに新しいブロックが来ない」は「テストネットが止まった」と同じではありません。私たちの船も、この記事の最初の下書きも、前者を後者と読みました。次からは、停止と呼ぶ前にノードとネットワークの接続を確かめます。
- 見るべきなのは負荷だけではありません。今回は静かなチェーンで起きたので、送った支払いの数だけでなく、ノードが新しいブロックごとに何をしているかも見ています。
- 短い寄港も結果のひとつです。そのまま見せます。90 分のうち 12 分、緑ではなく琥珀色で。""",
        },
    },
}
