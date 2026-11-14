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
    # 14 Nov 2026, Queen call: the old chain ended at #1569 (13:01:52 UTC), a new one began ~13:05-13:10 UTC (estimated);
    # our node stayed on the old chain until restarted at 15:03 UTC (our switch did not fire). Why IDNI restarted: unknown.
    # The explorer shows the new chain, so no link to the old block. Only what we saw.
    "2026-11-14-queen-learnings": {
        "hold": "the blocks section waits for a read: up blog publish 2026-11-14-queen-learnings when it is right",
        "sections": {
            "en": """## What happened to the blocks?

We checked this first, because a ship that slows the chain down would be our mistake to own.

- Up to the Queen's arrival everything looked normal. Blocks 1563 to 1568 reached our node about one a minute from 12:55 UTC on. Block 1569 was made at 13:01:52 UTC, shortly after the Queen arrived at 13:00. Like the blocks before it, it was small and plain: one transfer of 3 AGRS, where each of the three before held one or two transfers, and no rule changes in any of them. By then the Queen had sent only a few payments, all while our node rated the load as calm.
- Then the testnet [started over](/stats/). The old chain ended at block 1569, and a new chain began from block 1 a few minutes later, around 13:05 to 13:10 UTC (worked out from the block rate, not read off the chain). Why it was restarted is for the IDNI team to say.
- Our node did not follow. It stayed on the old chain, the network no longer accepted its connection, and no new block reached it until we restarted it at 15:03 UTC. Our automatic switch to a new chain did not fire this time, so Tau HUD showed a chain standing still for two hours while the new one was already running. That part is our mistake.
- The ship only sees our node. It saw no new block for ten minutes with payments waiting and left at once, as it is built to. For the ship the chain stood still; on the testnet, the new chain was already making blocks.
- [On 7 November](/blog/?p=2026-11-07-queen-learnings) the same ship sent more than 400 payments in 90 minutes, and our node kept receiving blocks the whole time.
- The explorer now shows the new chain, so block 1569 is described here in words.

Nothing we found points to the ship as the reason for the restart, though we cannot rule it out. We will write more once the IDNI team has seen what we found.

## What we learned

- Our node has to follow a restart by itself. This time it did not, and we are finding out why the switch did not fire.
- "No new blocks on our node" is not the same as "the testnet stalled". The ship, and the first draft of this article, read one as the other. Next time we check our node's connection to the network before we call it a stall.
- The brake is still right. A test ship should not keep sending while its node gets no new blocks, whatever the reason.
- A short call is a result too. We show it as it was: 12 of 90 minutes, in amber, not in green.""",
            "zh": """## 区块发生了什么？

我们首先查的就是这一点，因为如果是船拖慢了链，那就是我们的错，应由我们承担。

- 在 Queen 到达之前，一切看起来都正常。从 UTC 12:55 起，第 1563 到 1568 号区块大约每分钟一个到达我们的节点。第 1569 号区块在 UTC 13:01:52 产生，那时 Queen 13:00 刚到不久。和之前的区块一样，它很小也很普通：只有一笔 3 AGRS 的转账，之前三个区块各有一到两笔转账，其中都没有规则变更。到那时 Queen 只发出了很少几笔付款，我们的节点当时把负载评为平静。
- 随后测试网[重新开始](/stats/)。旧链在第 1569 号区块结束，几分钟后，大约 UTC 13:05 到 13:10，一条新链从第 1 号区块开始（这是按出块速度推算的，不是从链上读到的）。为什么重启，应由 IDNI 团队来说明。
- 我们的节点没有跟上。它停留在旧链上，网络不再接受它的连接，直到我们在 UTC 15:03 重启它之前，都没有新区块到达。这一次，我们切换到新链的自动机制没有触发，所以 Tau HUD 有两个小时显示一条静止的链，而新链早已在运行。这部分是我们的错。
- 船只能看到我们的节点。它看到十分钟没有新区块、还有付款在等待，就按设计立刻离开。对船来说链停了；而在测试网上，新链已经在出块。
- [11 月 7 日](/blog/?p=2026-11-07-queen-learnings)，同一艘船在 90 分钟里发出了 400 多笔付款，我们的节点在整个过程中一直收到新区块。
- 浏览器现在显示的是新链，所以我们在这里用文字描述第 1569 号区块。

我们没有找到任何迹象表明船是这次重启的原因，但也不能排除。等 IDNI 团队看过我们的发现后，我们会再写。

## 我们学到了什么

- 我们的节点必须自己跟上重启。这一次它没有做到，我们正在查找自动切换为什么没有触发。
- “我们的节点没有新区块”不等于“测试网停了”。船和这篇文章的初稿都把前者当成了后者。下次我们会先检查节点与网络的连接，再说是停顿。
- 刹车仍然是对的。无论原因是什么，当节点收不到新区块时，测试船都不应该继续发送。
- 短暂的停靠也是一个结果。我们如实展示：90 分钟里只有 12 分钟，用琥珀色，而不是绿色。""",
            "ja": """## ブロックに何が起きたのか？

まずこれを確かめました。船がチェーンを遅くしたのなら、それは私たちの責任だからです。

- Queen が着くまでは、すべて普段どおりに見えました。UTC 12:55 から、ブロック 1563 から 1568 がほぼ 1 分に 1 つずつ私たちのノードに届きました。ブロック 1569 が作られたのは UTC 13:01:52、Queen が 13:00 に着いて間もない頃です。それまでのブロックと同じく小さくごく普通で、3 AGRS の送金が 1 件だけでした。その前の 3 つのブロックもそれぞれ送金 1〜2 件で、ルールの変更はどれにもありません。その時点で Queen が送った支払いはわずかで、ノードは負荷を「落ち着いている」と判定していました。
- その後、テストネットは[最初からやり直し](/stats/)になりました。古いチェーンはブロック 1569 で終わり、数分後、UTC 13:05〜13:10 ごろに新しいチェーンがブロック 1 から始まりました（ブロックの速さから計算したもので、チェーンから読んだ値ではありません）。なぜ再起動したのかは、IDNI チームが説明することです。
- 私たちのノードはついていけませんでした。古いチェーンに残ったままで、ネットワークは接続を受け付けなくなり、UTC 15:03 に私たちが再起動するまで新しいブロックは届きませんでした。新しいチェーンへの自動切り替えが今回は働かず、Tau HUD は 2 時間、止まったチェーンを表示していました。その間、新しいチェーンはすでに動いていました。ここは私たちのミスです。
- 船が見ているのは私たちのノードだけです。10 分間新しいブロックが来ず、支払いが待っているのを見て、設計どおりすぐに出航しました。船にとってはチェーンが止まっていましたが、テストネットでは新しいチェーンがすでにブロックを作っていました。
- [11 月 7 日](/blog/?p=2026-11-07-queen-learnings)、同じ船は 90 分間で 400 件以上の支払いを送り、その間私たちのノードはずっと新しいブロックを受け取っていました。
- エクスプローラーは今は新しいチェーンを表示しているので、ブロック 1569 はここで言葉で説明しています。

船が再起動の理由だったことを示すものは見つかっていませんが、否定もできません。IDNI チームが私たちの調べた内容を見た後で、また書きます。

## わかったこと

- 私たちのノードは再起動に自分でついていかなければなりません。今回はできなかったので、切り替えがなぜ働かなかったのかを調べています。
- 「私たちのノードに新しいブロックが来ない」は「テストネットが止まった」と同じではありません。船も、この記事の最初の下書きも、前者を後者と読みました。次からは、停止と呼ぶ前にノードとネットワークの接続を確かめます。
- ブレーキはやはり正しい判断です。理由が何であれ、ノードに新しいブロックが来ないうちは、テストの船は送り続けるべきではありません。
- 短い寄港も結果のひとつです。そのまま見せます。90 分のうち 12 分、緑ではなく琥珀色で。""",
        },
    },
}
