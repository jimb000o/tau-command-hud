"""Parts written by hand for a drafted article (blog.py puts them into the draft the model wrote), and drafts held back
from publishing themselves until the owner has read them.

  NOTES["<article id>"] = {
      "hold": "why it waits",          # never published by itself (auto_publish); up blog publish <id> as always
      "title": {"en", "zh", "ja"}, "dek": {...}, "why": [{...}, ...], "card": [lines], "x": "...",   # set by hand
      "body": {"en": "## ...", "zh": ..., "ja": ...},      # a whole body in place of the model's
      "sections": {"en": "## ...", "zh": ..., "ja": ...},  # Markdown, put in before the body's last section
      "replace": [["en", "old words", "new words"], ...],  # words of the model's body
  }

What the model wrote stays in the draft (as_drafted, body_model), so changing a note here and `up blog` puts the new
text in, never twice, and taking a part out gives the model's back. A card set by hand makes the hero picture anew.
Only what we saw and can show; nothing that IDNI has not been told yet."""

FOOT = "Tau HUD blog · community project, not affiliated with IDNI"
STATS = "/stats/"                                   # chain restarts, read from our own node
BEFORE = "/blog/?p=2026-11-07-queen-learnings"      # the Queen's call of 7 November

NOTES: dict[str, dict] = {
    # 15 Nov 2026, the Queen's make-up call: the testnet started over again 8 minutes after she landed (old chain ended at
    # #1457, 14:07:54 UTC), the second time in two days during her call; the ships are paused. Its draft waits for Kilian.
    "2026-11-15-queen-learnings": {
        "hold": "the testnet restarted during this call too; read it and decide with Kilian before anything goes out",
    },
    # 14 Nov 2026, Queen call (rewritten by hand on Kilian's ask): the old chain ended at #1569 (13:01:52 UTC), a new one
    # began ~13:05-13:10 UTC (estimated from the block rate); our node stayed on the old chain until restarted at 15:03 UTC
    # (it did not reconnect on its own; a node restart fixed it, why is still open). Why IDNI restarted: unknown. The explorer shows the new
    # chain, so no link to the old block. Numbers: the visit's tiles (12/90 minutes, 8 accepted, 12 no answer, 517 skipped).
    "2026-11-14-queen-learnings": {
        "hold": "rewritten by hand: up blog publish 2026-11-14-queen-learnings after a read",
        "title": {
            "en": "Queen Mempool's call cut short by a testnet restart",
            "zh": "测试网重启，Queen Mempool 的停靠提前结束",
            "ja": "テストネットの再起動で Queen Mempool の寄港が途中で終了",
        },
        "dek": {
            "en": "The chain started over minutes into her visit, and our node took two hours to rejoin. What happened, and what we change.",
            "zh": "她到达几分钟后，链就重新开始了，而我们的节点花了两个小时才重新连上。发生了什么，我们要改什么。",
            "ja": "寄港から数分でチェーンが最初からやり直しになり、私たちのノードが戻るまで 2 時間かかりました。何が起きたのか、何を変えるのか。",
        },
        "why": [
            {"en": "A restart of the testnet ended the Queen's call after 12 of 90 minutes, a pity for a voyage that had only just begun.",
             "zh": "测试网重启让 Queen 的停靠在 90 分钟里只进行了 12 分钟就结束了，对一次刚刚开始的航行来说很可惜。",
             "ja": "テストネットの再起動で、Queen の寄港は 90 分のうち 12 分で終わりました。始まったばかりの航海だっただけに残念です。"},
            {"en": "Our node took two hours to rejoin the network after the restart. Next time a watchdog will catch that within minutes.",
             "zh": "重启后，我们的节点花了两个小时才重新连上网络。下次，一个看门程序会在几分钟内发现这种情况。",
             "ja": "再起動の後、私たちのノードがネットワークに戻るまで 2 時間かかりました。次は監視の仕組みが数分で気づきます。"},
            {"en": "The ship's brake worked: with no new blocks, it stopped sending at once.",
             "zh": "船的刹车起了作用：没有新区块时，它立刻停止发送。",
             "ja": "船のブレーキは働きました。新しいブロックが来ないと、すぐに送るのをやめました。"},
        ],
        "card": [
            "Queen Mempool's call cut short by a testnet restart",
            "The chain started over minutes into her visit",
            "## Why it matters",
            "- Old chain ended at block 1569, call over at 12 min",
            "- Our node took two hours to rejoin the network",
            "- Brake worked: no sending into a chain gone still",
            FOOT,
        ],
        "x": "A testnet restart cut the Queen Mempool's call short after 12 of 90 minutes. Our node took two hours to rejoin; "
             "next time a watchdog catches that within minutes.",
        "body": {
            "en": f"""## Update, 15 November

On her make-up call the next day, the testnet started over again, 8 minutes after the Queen landed: the old chain ended at block 1457 at 14:07:54 UTC, and the new one began at 14:09:39 UTC. Two restarts within minutes of the same ship's arrival, on two days in a row, are hard to call chance. So we no longer write that nothing points to the ship: her traffic may be connected, though we do not know how, and why the testnet restarts is for the IDNI team to say. We have paused the cruise ships until we understand it.

One thing did work this time: our node followed the new chain within seconds, and the ship's logbook told the restart as a restart.

## What happened

The Queen Mempool arrived at White Rabbit Key at 13:00 UTC for a 90-minute call. A few minutes later the testnet started over from its starting state, and her call ended after 12 minutes. Our node accepted 8 of her payments; 12 more got no answer in time, and 517 planned stops were skipped.

It is a pity. The Queen had only just begun her round when the chain under her ended, so this voyage tells us little about the ship itself. What it does tell us is how a restart looks from our side, and where our side fell short.

## What happened to the blocks

We checked first whether the ship could have caused it, because that would be our mistake to own.

- Up to the Queen's arrival everything looked normal. Blocks 1563 to 1568 reached our node about one a minute from 12:55 UTC on. Block 1569 was made at 13:01:52 UTC. Like the blocks before it, it was small and plain: one transfer of 3 AGRS, where each of the three before held one or two transfers, and no rule changes in any of them. By then the Queen had sent only a few payments, all while our node rated the load as calm.
- Then the testnet [started over]({STATS}). The old chain ended at block 1569, and a new chain began from block 1 a few minutes later, around 13:05 to 13:10 UTC (worked out from the block rate, not read off the chain). It runs the same software as before. Why it was restarted is for the IDNI team to say.
- Restarts wipe balances, rules and history. Whatever the Queen's passengers paid in those first minutes went with the old chain.
- [On 7 November]({BEFORE}) the same ship sent more than 400 payments in 90 minutes, and our node kept receiving blocks the whole time. At the time we found nothing pointing to the ship as the reason for the restart, but we could not rule it out (see the update above).

## What happened on our side

Our node didn't reconnect on its own afterwards; a node restart fixed it. Until then it stayed on the old chain and every attempt to connect to the network failed, so no new block reached it until we restarted the node at 15:03 UTC. The connection then worked at once, and the node caught up with the new chain, 117 blocks, within minutes. Why reconnecting failed before that is still being looked at.

So for two hours Tau HUD showed the old chain standing still. We would rather catch that within minutes, and that is what the first change below is for.

The ship only sees our node. It saw no new block for ten minutes with payments waiting and left at once, as it is built to. That brake did its job: it did not keep sending into a chain that had gone still. But the ship's own report called it a stall of the testnet, and that was not what happened.

## What we learned and what we change

- **A node that loses the network has to notice by itself.** We have built a watchdog, and it has been running since the same afternoon: when our node cannot reach the network for ten minutes, it restarts itself, which is what fixed it this time. If that does not help, it waits longer before each next try. Today's two hours would have been about ten minutes.
- **"No new blocks on our node" is not "the testnet stalled".** The ship will write a plain note in its logbook when the chain under it stops or starts over, and check our node's connection before it calls anything a stall.
- **The brake stays as it is.** A test ship should not send while its node gets no new blocks, whatever the reason.
- **A short call is a result too.** We show it as it was: 12 of 90 minutes, in amber, not in green.

## What is still open

- Why the testnet was restarted at that moment. When the IDNI team says, we will add it here.
- Whether the Queen's traffic and the restarts are connected. Until we know, the cruise ships stay in port.""",
            "zh": f"""## 更新，11 月 15 日

在第二天补的那次停靠中，测试网又一次重新开始了，就在 Queen 到达 8 分钟后：旧链在 UTC 14:07:54 于第 1457 号区块结束，新链在 UTC 14:09:39 开始。连续两天，两次重启都发生在同一艘船到达后几分钟内，很难说是巧合。所以我们不再写“没有迹象指向船”：她的流量可能与此有关，但我们不知道是怎样的关系，而测试网为什么重启，应由 IDNI 团队来说明。在弄清楚之前，我们暂停了所有游轮。

这一次有一件事做对了：我们的节点在几秒内就跟上了新链，船的日志也把这次重启如实记作重启。

## 发生了什么

Queen Mempool 在 UTC 13:00 到达 White Rabbit Key，计划停靠 90 分钟。几分钟后，测试网从初始状态重新开始，她的停靠在 12 分钟后结束。我们的节点接受了她的 8 笔付款；另有 12 笔没有及时得到回应，517 个计划中的停靠点被跳过。

这很可惜。Queen 才刚开始她的行程，脚下的链就结束了，所以这次航行几乎说明不了船本身的情况。它说明的是：从我们这边看，一次重启是什么样子，以及我们这边哪里做得不够。

## 区块发生了什么

我们首先查的是船是否可能造成了这件事，因为如果是，那就是我们的错，应由我们承担。

- 在 Queen 到达之前，一切看起来都正常。从 UTC 12:55 起，第 1563 到 1568 号区块大约每分钟一个到达我们的节点。第 1569 号区块在 UTC 13:01:52 产生。和之前的区块一样，它很小也很普通：只有一笔 3 AGRS 的转账，之前三个区块各有一到两笔转账，其中都没有规则变更。到那时 Queen 只发出了很少几笔付款，我们的节点当时把负载评为平静。
- 随后测试网[重新开始]({STATS})。旧链在第 1569 号区块结束，几分钟后，大约 UTC 13:05 到 13:10，一条新链从第 1 号区块开始（这是按出块速度推算的，不是从链上读到的）。它运行的软件和之前相同。为什么重启，应由 IDNI 团队来说明。
- 重启会清除余额、规则和历史。Queen 的乘客在最初几分钟里付的款，也随旧链一起消失了。
- [11 月 7 日]({BEFORE})，同一艘船在 90 分钟里发出了 400 多笔付款，我们的节点在整个过程中一直收到新区块。当时我们没有找到迹象表明船是这次重启的原因，但也不能排除（见上面的更新）。

## 我们这边发生了什么

重启之后，我们的节点没有自己重新连上。它停留在旧链上，每次连接网络的尝试都失败了，所以直到我们在 UTC 15:03 重启节点之前，都没有新区块到达。之后连接立刻恢复，节点在几分钟内追上了新链，共 117 个区块。在那之前为什么无法重新连接，仍在查看中。

所以 Tau HUD 有两个小时显示一条静止的旧链。我们希望在几分钟内就发现这种情况，下面的第一项改动就是为此。

船只能看到我们的节点。它看到十分钟没有新区块、还有付款在等待，就按设计立刻离开。刹车起了作用：它没有继续往一条静止的链里发送。但船自己的报告把它叫作测试网的停顿，而事实并非如此。

## 我们学到了什么，要改什么

- **失去网络的节点必须自己察觉。** 我们已经做好了一个看门程序，当天下午起就已在运行：当我们的节点十分钟连不上网络时，它会自动重启（这次正是重启解决了问题）；如果重启没用，每次再试之前会等得更久。今天的两个小时，本来大约十分钟就能解决。
- **“我们的节点没有新区块”不等于“测试网停了”。** 当脚下的链停下或重新开始时，船会在日志里写下清楚的说明，并在把任何情况叫作停顿之前，先检查我们节点的连接。
- **刹车保持不变。** 无论原因是什么，当节点收不到新区块时，测试船都不应该发送。
- **短暂的停靠也是一个结果。** 我们如实展示：90 分钟里只有 12 分钟，用琥珀色，而不是绿色。

## 仍待解答

- 测试网为什么在那个时候重启。IDNI 团队说明后，我们会补充在这里。
- Queen 的流量和这些重启是否有关。在弄清楚之前，游轮都留在港口。""",
            "ja": f"""## 更新（11 月 15 日）

翌日のやり直しの寄港でも、Queen が着いて 8 分後にテストネットはまた最初からやり直しになりました。古いチェーンは UTC 14:07:54 にブロック 1457 で終わり、新しいチェーンは UTC 14:09:39 に始まりました。2 日続けて、同じ船の到着から数分で再起動が起きたことを、偶然とは言いにくいです。そのため「船を示すものはない」とはもう書きません。彼女の通信が関係しているかもしれませんが、どう関係しているのかはわかりません。テストネットがなぜ再起動するのかは、IDNI チームが説明することです。理由がわかるまで、クルーズ船は休止しています。

今回うまくいったこともあります。私たちのノードは数秒で新しいチェーンについていき、船の航海日誌も再起動を再起動として記録しました。

## 何が起きたのか

Queen Mempool は UTC 13:00 に White Rabbit Key に着き、90 分の寄港を予定していました。数分後、テストネットは初期状態から最初からやり直しになり、寄港は 12 分で終わりました。私たちのノードは彼女の支払いのうち 8 件を受け付け、さらに 12 件は時間内に応答がなく、予定していた 517 か所の立ち寄りは飛ばされました。

残念です。Queen が回り始めたばかりのところで足元のチェーンが終わったので、この航海から船そのものについてわかることはほとんどありません。わかるのは、再起動が私たちの側からどう見えるか、そして私たちの側のどこが足りなかったかです。

## ブロックに何が起きたのか

まず、船が原因になりえたかを確かめました。もしそうなら、それは私たちの責任だからです。

- Queen が着くまでは、すべて普段どおりに見えました。UTC 12:55 から、ブロック 1563 から 1568 がほぼ 1 分に 1 つずつ私たちのノードに届きました。ブロック 1569 が作られたのは UTC 13:01:52 です。それまでのブロックと同じく小さくごく普通で、3 AGRS の送金が 1 件だけでした。その前の 3 つのブロックもそれぞれ送金 1〜2 件で、ルールの変更はどれにもありません。その時点で Queen が送った支払いはわずかで、ノードは負荷を「落ち着いている」と判定していました。
- その後、テストネットは[最初からやり直し]({STATS})になりました。古いチェーンはブロック 1569 で終わり、数分後、UTC 13:05〜13:10 ごろに新しいチェーンがブロック 1 から始まりました（ブロックの速さから計算したもので、チェーンから読んだ値ではありません）。動いているソフトウェアは以前と同じです。なぜ再起動したのかは、IDNI チームが説明することです。
- 再起動では残高、ルール、履歴が消えます。Queen の乗客が最初の数分に支払った分も、古いチェーンと一緒に消えました。
- [11 月 7 日]({BEFORE})、同じ船は 90 分間で 400 件以上の支払いを送り、その間私たちのノードはずっと新しいブロックを受け取っていました。その時点では船が再起動の理由だったことを示すものは見つかりませんでしたが、否定もできませんでした（上の更新を参照）。

## 私たちの側で起きたこと

再起動の後、私たちのノードは自分ではつなぎ直せませんでした。古いチェーンに残ったままで、ネットワークへの接続はすべて失敗し、UTC 15:03 にノードを再起動するまで新しいブロックは届きませんでした。再起動するとすぐに接続でき、数分で新しいチェーンの 117 ブロックに追いつきました。それまでなぜつなぎ直せなかったのかは、まだ調べています。

そのため Tau HUD は 2 時間、止まった古いチェーンを表示していました。これは数分で気づきたいところで、下の最初の変更はそのためのものです。

船が見ているのは私たちのノードだけです。10 分間新しいブロックが来ず、支払いが待っているのを見て、設計どおりすぐに出航しました。このブレーキは役目を果たし、止まったチェーンに送り続けることはありませんでした。ただ、船自身の報告はこれをテストネットの停止と呼びましたが、実際に起きたことは違いました。

## わかったこと、変えること

- **ネットワークを失ったノードは、自分で気づかなければなりません。** 監視の仕組みを作り、同じ日の午後から動いています。ノードが 10 分間ネットワークにつながらないとき、自分で再起動します。今回直したのも再起動でした。それでもだめなら、次に試すまでの間隔を延ばします。今日の 2 時間は、10 分ほどで済んだはずです。
- **「私たちのノードに新しいブロックが来ない」は「テストネットが止まった」ではありません。** 足元のチェーンが止まったり最初からやり直しになったりしたとき、船は航海日誌にはっきり書き残し、停止と呼ぶ前にノードの接続を確かめます。
- **ブレーキはこのままにします。** 理由が何であれ、ノードに新しいブロックが来ないうちは、テストの船は送るべきではありません。
- **短い寄港も結果のひとつです。** そのまま見せます。90 分のうち 12 分、緑ではなく琥珀色で。

## まだわからないこと

- なぜあの時点でテストネットが再起動したのか。IDNI チームが説明したら、ここに加えます。
- Queen の通信と再起動が関係しているのかどうか。わかるまで、クルーズ船は港に留まります。""",
        },
    },
}
