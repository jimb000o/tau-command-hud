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
    # 14 Nov 2026: the chain stood still during the Queen's call. Kilian asked for what we checked afterwards and what we
    # learned; the detail level beyond what anyone could see is his to decide (blog_notes level 1 = observable only).
    "2026-11-14-queen-learnings": {
        "hold": "the stall section waits for a read: up blog publish 2026-11-14-queen-learnings when it is right",
        "sections": {
            "en": """## Did the ship cause the stall?

We checked this first, because a ship that slows the chain down would be our mistake to own.

- The stall came on a calm chain. Blocks 1563 to 1568 reached our node about one a minute, from 12:55 UTC on. The last one, [block 1569](https://tauhud.com/explorer/?b=1569), was added at 13:01:56 UTC, shortly after the Queen arrived at 13:00. By then she had sent only a few payments, all while our node rated the load as calm. No block came after it while she was in port.
- [On 7 November](/blog/?p=2026-11-07-queen-learnings) the same ship sent more than 400 payments in 90 minutes, and the chain kept making blocks the whole time.
- Our node stayed up through the stall and kept taking in transfers: 21 were waiting when the ship left. What stopped was new blocks arriving.
- The ship did what it is built to do. When the newest block was more than ten minutes old with payments waiting, she left at once instead of adding more to a chain that stood still.

So the ship's load does not explain the stall. What does is still being checked, and we will write it up once the IDNI team has seen what we found.

## What we learned

- The stall brake is right. It made the call short, but a test ship should never pile onto a chain that is stuck. It stays as it is.
- Load is not the only thing to watch. This stall came on a quiet chain, so we now also look at what a node does with each new block, not only at how many payments go out.
- A short call is a result too. We show it as it was: 12 of 90 minutes, in amber, not in green.""",
            "zh": """## 是这艘船让链停下的吗？

我们首先查的就是这一点，因为如果是船拖慢了链，那就是我们的错，应由我们承担。

- 链停下时，网络很平静。从 UTC 12:55 起，第 1563 到 1568 号区块大约每分钟一个到达我们的节点。最后一个是[第 1569 号区块](https://tauhud.com/explorer/?b=1569)，在 UTC 13:01:56 加入，那时 Queen 13:00 刚到不久，只发出了很少几笔付款，我们的节点当时把负载评为平静。她停靠期间，之后再没有新区块。
- [11 月 7 日](/blog/?p=2026-11-07-queen-learnings)，同一艘船在 90 分钟里发出了 400 多笔付款，链在整个过程中一直在出块。
- 链停下期间，我们的节点一直在线，并继续接收转账：船离开时有 21 笔在等待。停下的是新区块的到来。
- 船做了它被设计要做的事：当最新区块已超过十分钟、还有付款在等待时，它立刻离开，而不是继续给一条停住的链加负担。

所以，船带来的负载解释不了这次停顿。真正的原因仍在核查中；等 IDNI 团队看过我们的发现后，我们再写出来。

## 我们学到了什么

- 停顿刹车是对的。它让这次停靠变得很短，但测试船绝不应该往一条卡住的链上继续堆交易。它保持不变。
- 负载不是唯一要看的东西。这次停顿发生在安静的链上，所以我们现在也看节点如何处理每一个新区块，而不只看发出了多少付款。
- 短暂的停靠也是一个结果。我们如实展示：90 分钟里只有 12 分钟，用琥珀色，而不是绿色。""",
            "ja": """## 船がチェーンを止めたのか？

まずこれを確かめました。船がチェーンを遅くしたのなら、それは私たちの責任だからです。

- 停止は落ち着いたチェーンで起きました。UTC 12:55 から、ブロック 1563 から 1568 がほぼ 1 分に 1 つずつ私たちのノードに届きました。最後の[ブロック 1569](https://tauhud.com/explorer/?b=1569) が加わったのは UTC 13:01:56、Queen が 13:00 に着いて間もない頃です。その時点で送った支払いはわずかで、ノードは負荷を「落ち着いている」と判定していました。寄港中、その後のブロックは来ませんでした。
- [11 月 7 日](/blog/?p=2026-11-07-queen-learnings)、同じ船は 90 分間で 400 件以上の支払いを送り、その間チェーンはずっとブロックを作り続けました。
- 停止の間も私たちのノードは動き続け、送金を受け付けていました。船が去ったとき 21 件が待っていました。止まったのは新しいブロックの到着です。
- 船は設計どおりに動きました。最新のブロックが 10 分以上前のもので支払いが待っているとき、止まったチェーンにさらに積み上げず、すぐに出航しました。

つまり、船の負荷では今回の停止を説明できません。原因はまだ調べています。IDNI チームが私たちの調べた内容を見た後で、記事にします。

## わかったこと

- 停止ブレーキは正しい判断でした。寄港は短くなりましたが、テストの船が止まったチェーンに積み上げるべきではありません。このままにします。
- 見るべきなのは負荷だけではありません。今回は静かなチェーンで止まったので、送った支払いの数だけでなく、ノードが新しいブロックごとに何をしているかも見ています。
- 短い寄港も結果のひとつです。そのまま見せます。90 分のうち 12 分、緑ではなく琥珀色で。""",
        },
    },
}
