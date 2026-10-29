/* 『コンセンサス日報』日本語版。構成は index.html の英語版と一対一で対応：class="u" のひとつひとつが 1 本の記事。 */
window.GAZETTE_JA = {
  name: "コンセンサス日報",
  motto: "「ルールが合意で変わる場所」",
  ui: { amb0: "カフェ：オフ", amb1: "カフェ：静か", amb2: "カフェ：にぎやか", hitCup: "コーヒーをかき混ぜる", hitSugar: "角砂糖", hitPapers: "昨日の新聞", notes: {
    cup: (h, a) => h != null ? `湯気が τ の字を描く。ブロック #${h.toLocaleString("en-US")} がテストネットの最新${a != null ? `、${a} 秒前に生成` : ""}。次のブロックはおよそ 8 秒ごとにやって来る。` : "湯気が τ の字を描く。テストネットでは、およそ 8 秒ごとに新しいブロックが生まれる。",
    sugar: () => "ひと粒、またひと粒と、ひとつの鎖に。どのブロックも、加わる前に施行中のルールと照らして検査される。",
    papers: h => `号外！ Tau ではルールが合意で変わる：提案され、投票され、適用の前に論理で検査される。フォークは要らない。${h != null ? `ブロック #${h.toLocaleString("en-US")} 時点。` : ""}` }, rOut: "サイトのメニューを表示", rIn: "画面いっぱいに読む", rFull: "全画面", rLarge: "大きな文字、1 記事ずつ", rWhole: "紙面全体", hintZoom: "<b>タップ</b>でめくる · <b>ダブルタップ</b>かピンチで拡大", week: "今週", weekNo: n => `週刊版 · 第 ${n} 号`, weekEar: "今週の紙面", weather: "チェーンの天気", weekAlt: "Tau HUD の画面の網点写真", weekCap: "<b>今週の中核。</b>Tau HUD はテストネットのすべてのブロックを、生成されるそばから追っている。軌道上の点はそれぞれノード。バリデーターが合意すると輪が閉じる。", weekOf: "対象週", figures: "数字で見る今週", founding: "創刊特集", foundingP: "Tau の 12 年。2014 年のフォーラムへの投稿から、利用者が投票でルールを変えるチェーンまで。ページをめくってどうぞ。", weekNote: "非公式のコミュニティプロジェクト Tau HUD が、公開テストネットとシミュレーションを読み取って作成。テストネットの AGRS は練習用で、価値はない。毎週月曜に新しい号。「読者へのお知らせ」の全文は最終面に。", free: "無料", freeP: "非公式のコミュニティ観測器 Tau HUD 発行。", coverLine: "Tau の 12 年と、自らのルールを変えるチェーン。ニュース、投書、追悼、パズルの全 10 面。", cont: "前面から続く", stop: "最新電報", faith: "植字室より：本紙は学習する機械が組んでおり、たいていはうまく推し量るが、ときには外す。Tau はその逆の造りで、すべてのルールを適用前に検査する論理の機械である。本紙は善意でお読みいただきたい。証拠はチェーンにある。", front: "一面", pageN: n => `第 ${n} 面`, pagesN: (a, b) => `第 ${a}〜${b} 面`, of: "/", tocN: n => `${n} 面`, back: "‹ 戻る", turn: "めくる ›", contents: "目次", pocket: "ポケット版", broad: "大判", sOn: "音オン", sOff: "音オフ", hint: "<b>紙面をクリックかタップ</b>でめくる · 矢印キーも使える", hintTouch: "<b>紙面をタップ</b>でめくる · スワイプも使える", wireWait: "ノードへの電信線を接続中", wireOff: "ノードへの電信線はいま沈黙している。詳しくは tauhud.com で", wire: (h, age) => `印刷の時点で、テストネットはブロック <span class="live">#${h}</span> にあった${age != null ? `。最新のブロックは、この行が組まれる ${age} 秒前に生成された` : ""}。ライブの動きは tauhud.com で。` },
  date: d => d.toLocaleDateString("ja-JP", { weekday: "long", year: "numeric", month: "long", day: "numeric", timeZone: "UTC" }),
  toc: ["一面：利用者がチェーンの法を書き換える", "Zennet からの長い道", "ハードフォークとは", "静かな 4 年と、ひとつの偉大な方程式", "自らを語る言語", "工事現場からの電報：2025", "利用者がハンドルを握った年", "法はどうつくられるか · 投書", "今日のテストネット · 案内広告", "娯楽 · 切り抜いて保存"],
  pages: [
/* ---------------- 1 一面 ---------------- */
`<div class="pg front">
  <div class="mast">
    <div class="ear"><b>チェーンの天気</b>晴れ。およそ 8 秒ごとにブロック。当番のバリデーターは 1 名。見通し：気候は投票で変更可能。</div>
    <div><div class="title">{{NAME}}</div><div class="motto">{{MOTTO}}</div></div>
    <div class="ear r"><b>無料</b>非公式のコミュニティ観測器 Tau HUD 発行。テストネットの AGRS は練習用。</div>
  </div>
  <div class="dateline"><span>第 13 巻 · No. {{HEIGHT}}</span><span>{{DATE}}</span><span>tauhud.com</span></div>
  <div class="center"><span class="extra">号外</span></div>
  <div class="banner">利用者が投票でチェーンの法を書き換え：フォークなし、再起動なし</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">テストネット Alpha · 特報</div>
      <h2>利用者の投票でチェーンの合意方法が変わり、すべてのノードが自ら従う</h2>
      <div class="deck">合意は固定のバリデーターリストからプルーフ・オブ・ステークへ、そしてまた元へ。1 台のマシンも入れ直さずに。技術者たちは、利用者自身が統治するブロックチェーンの初の本格的な実演だと呼ぶ。</div>
      <figure class="photo"><img src="img/hud-wide.jpg" width="1100" height="450" style="height:auto;aspect-ratio:1100/450" alt="Tau HUD の画面の網点写真"><figcaption><b>本紙のカメラは中核へ。</b>tauhud.com のコミュニティ観測器 Tau HUD は、テストネットがブロックを生成するたびにそれを追う。軌道上の点はそれぞれノード。バリデーターが合意すると輪が閉じる。</figcaption></figure>
      <div class="c2"><p class="dc ni">どのブロックチェーンにも規則集がある。たいていのチェーンでは、それはソフトウェアそのものに刻まれており、1 行を変えるだけで<i>ハードフォーク</i>になる。新しいソフトウェアがすべてのマシンに送られ、すべての運用者がそれを入れ、そして誰かが拒んでチェーンが二つに割れる危険が常につきまとう。</p>
      <p>Tau のネットワークは別の道を選んだ。チームは 8 月の開発報告でいくつかの実演を紹介した。彼らの言葉を借りれば、コミュニティは<i>「ネットワークの法の一条項を変更し、次のブロックで有効にできる」</i>。どのノードも変更も再配置も要らない。</p>
      <p>その条項は小さなものではない。合意そのもの、つまり誰がブロックを生成できるかである。利用者は投票で固定のバリデーターリストからプルーフ・オブ・ステークへ移り、その後また投票で戻した。そのたびに、すべてのノードが約束のブロックで自ら切り替わった。</p>
      <p>それが可能なのは、規則集がチェーンの上にあるからだ。1 月以降、すべてのブロックは自らが従ったルールのスナップショットを記録している。5 月以降、合意のロジックは Python ではなく Tau 言語で書かれており、ルールを変えることは単なるもう一つのトランザクションになった。<i>詳しくは第 7 面。</i></p></div>
    </div>
    <div class="u s2 rl">
      <h3>12 年がかりの仕事</h3>
      <p class="ni">物語は 2014 年、Zennet という共有スーパーコンピューターと、インターネットのフォーラムでのある会話から始まる。2015 年に Tau-Chain と Agoras になり、2017 年に「新しい Tau」に、2024 年に言語に、2025 年に動くテストネットになった。<i>全文は第 2〜7 面。</i></p>
      <hr class="rule2">
      <h3>誰でも見物できる</h3>
      <p class="ni">テストネットは公開されている。Tau HUD は創設チームのブートノードの隣で自前のノードを動かし、すべてのブロック、すべての投票、すべてのルール変更をライブで見せている。静かな時間にはシミュレーションもある。<i>第 9 面参照。</i></p>
      <hr class="rule2">
      <div class="idx"><h3>本号の内容</h3>
        <p>Zennet から<span></span>2</p>
        <p>なぜ他のチェーンはフォークするのか<span></span>3</p>
        <p>追悼<span></span>4</p>
        <p>自らを語る言語<span></span>5</p>
        <p>2025 年の電報<span></span>6</p>
        <p>投票所の機械<span></span>7</p>
        <p>投書<span></span>8</p>
        <p>案内広告<span></span>9</p>
        <p>パズル<span></span>10</p>
      </div>
      <div class="ad inv"><div class="t">フォーク無用！</div><p>クラブが会則を改めるようにルールを変える唯一のチェーン：投票し、記録し、次の会合から施行。</p></div>
    </div>
  </div>
  <div class="stop"><b>最新電報</b><span id="wire0">{{WIRE}}</span></div>
  <div class="faith">{{FAITH}}</div>
</div>`,
/* ---------------- 2 起源 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 2 面</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">スーパーコンピューター、フォーラムの見知らぬ人、そして消えない考え</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">起源 · 2014〜2017</div>
      <h2>Zennet からの長い道</h2>
      <div class="by">本紙歴史部</div>
      <div class="c2"><p class="dc ni">2014 年 8 月、Ohad Asor というソフトウェア開発者が bitcointalk のフォーラムに Zennet を投稿した。誰もが余った計算能力を貸し出し、ブロックチェーンで報酬を受け取れる、公開の分散型スーパーコンピューターである。</p>
      <p>Zennet は主役であり続けたわけではない。Asor が <i>HunterMinerCrafter</i> と名乗るフォーラムのメンバーとそれについて議論するうちに、はるかに大きな考えを耳にした。使う人たち自身がルールを変えられるチェーンである。彼はその考えを自分のものだと言ったことは一度もない。</p>
      <div class="q">「Tau のアイデアは私のものではない。私は Zennet を思いつき、それから ‘Hunter Miner Crafter’ に出会った……あるとき、彼が Tau のアイデアを話してくれた。」<small>Ohad Asor、2016 年のインタビュー</small></div>
      <p>2015 年 2 月、計画は Tau-Chain（基盤）と Agoras（その上に築かれる市場）の名で公になった。Zennet の計算能力の市場は、Agoras の市場の一つとなった。</p>
      <p>2016 年 8 月、最初の解説動画が公開された。Tau はブロックチェーンを伴う言語であり、各ブロックが次のブロックを受け入れる条件を持つ、と動画は語った。言い換えれば、ネットワークのルールは変えられる。</p>
      <p>そして空白が訪れる。1 年間ブログの更新がなかったのち、Asor は 2017 年の大みそかに「新しい Tau」を発表した。目標は大きくなっていた。ルールを変えられるチェーンだけでなく、意味を理解する機械の助けを借りて、非常に大きな集団が議論し合意できるようにすることである。</p>
      <div class="q">「一定の仮定のもとで、本当に効率よく拡大する議論に到達できる。」<small>「新しい Tau」、2017 年 12 月</small></div></div>
    </div>
    <div class="u s2 rl">
      <h3>百万人の対話</h3>
      <p class="ni">10 人に一つのルールで合意してもらえば、それは会議になる。百万人に頼めば、それは暴動になる。Tau の答えは、参加者それぞれに、機械が読めて推論できる言語で望みを述べてもらうことだ。そうすれば機械は、誰が誰と同意し、どこで意見が矛盾し、みんな合わせて実際に何を言ったのかを見分けられる。</p>
      <p>2016 年のインタビューでブロックチェーンの価値を問われたチームは、サトシ・ナカモトの言葉で答えた。<i>「誰もが書き込めて、誰も不正のできない公共の共有データベース」</i>。Tau はそれをルールと知識に対して行おうとしている。</p>
      <div class="box small"><p><b>AGORAS とは？</b>IDNI が 2015 年から描いている市場で、いずれ Tau の上に築かれる層。計算能力、仕様に照らして検査されたコード、専門家の助言を取引する。まだ将来の計画であり、製品ではない。今日テストネットにある AGRS は練習用である。</p></div>
      <div class="box small"><p><b>Ohad Asor とは？</b>Tau を手がける会社 IDNI の創設者。数学の素養を持つ開発者で、本人によれば論理学に深く入り込んだのは Tau に取り組み始めてからだという。</p></div>
    </div>
  </div>
</div>`,
/* ---------------- 3 ハードフォーク ---------------- */
`<div class="pg">
  <div class="rh"><span>第 3 面</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="kick">お忙しい読者のために</div>
  <div class="banner sm">ハードフォークとは何か、そして Tau になぜそれが要らないのか</div>
  <div class="grid">
    <div class="u full diag">
      <svg viewBox="0 0 760 250" aria-label="ルールを変える二つの方法">
        <defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" stroke="#1b1813" stroke-width="1.2"/></pattern>
        <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="#1b1813"/></marker></defs>
        <text x="0" y="22" font-size="17" font-weight="700" letter-spacing="2">昔ながらのやり方</text>
        <text x="0" y="40" font-size="13" font-style="italic">多くのブロックチェーン：何か月もかかり、分裂することもある</text>
        <g font-size="13" text-anchor="middle">
          <rect x="0" y="54" width="120" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="60" y="81">提案</text>
          <rect x="150" y="54" width="130" height="44" fill="url(#hatch)" opacity=".35"/><rect x="150" y="54" width="130" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="215" y="81" font-weight="700">何か月もの議論</text>
          <rect x="310" y="54" width="120" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="370" y="81">新しいソフト</text>
          <rect x="460" y="54" width="130" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="525" y="81">全員が更新</text>
          <line x1="120" y1="76" x2="148" y2="76" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="280" y1="76" x2="308" y2="76" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="430" y1="76" x2="458" y2="76" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/>
          <line x1="590" y1="76" x2="625" y2="60" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="590" y1="76" x2="625" y2="94" stroke="#1b1813" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#ar)"/>
          <text x="694" y="64" font-weight="700">チェーン A</text><text x="694" y="100" font-style="italic">チェーン B？</text>
        </g>
        <line x1="0" y1="126" x2="760" y2="126" stroke="#1b1813" stroke-width=".8"/>
        <text x="0" y="152" font-size="17" font-weight="700" letter-spacing="2">TAU のやり方</text>
        <text x="0" y="170" font-size="13" font-style="italic">ルール変更はトランザクションにすぎず、チェーンは常に一つ</text>
        <g font-size="13" text-anchor="middle">
          <rect x="0" y="184" width="120" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="60" y="211">提案</text>
          <rect x="150" y="184" width="130" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="215" y="204">論理で検査</text><text x="215" y="220" font-size="11" font-style="italic">矛盾？なら拒否</text>
          <rect x="310" y="184" width="120" height="44" fill="none" stroke="#1b1813" stroke-width="1.5"/><text x="370" y="204">合意</text><text x="370" y="220" font-size="11" font-style="italic">利用者の投票で</text>
          <rect x="460" y="184" width="130" height="44" fill="#1b1813"/><text x="525" y="204" fill="#efe5cf" font-weight="700">法</text><text x="525" y="220" font-size="11" fill="#efe5cf" font-style="italic">決めたブロックで施行</text>
          <line x1="120" y1="206" x2="148" y2="206" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="280" y1="206" x2="308" y2="206" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><line x1="430" y1="206" x2="458" y2="206" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/>
          <line x1="590" y1="206" x2="625" y2="206" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar)"/><text x="694" y="203" font-weight="700">一つのチェーン</text><text x="694" y="219" font-size="11" font-style="italic">全ノードが一斉に切り替え</text>
        </g>
      </svg>
      <div class="cap"><b>図 1。</b>ブロックチェーンのルールを変える二つの方法。Tau HUD の「ルールの変わり方」をもとに本紙作成。</div>
    </div>
    <div class="u s4 rt">
      <h2 class="l">他のチェーンではコードが法、Tau では合意が法</h2>
      <div class="c2"><p class="ni dc">ソフトウェアで書かれた規則集の困ったところは、プログラマーにしか開けず、しかも全員に新しい写しを配ることでしか変えられない点にある。ハードフォークとは、その写しの丁寧な言い方だ。拒む人が十分に多ければチェーンは割れ、二つの通貨は遺言の読み上げのあとで仲たがいした兄弟のように、別々の道を行く。</p>
      <p>Tau は規則集をチェーンの中に置く。利用者は論理の言語である Tau 言語でルールを書き、ほかのトランザクションと同じように提案する。提案は適用される前にコンパイルされ、施行中のルールと照らし合わされる。それらと矛盾するものは入口で拒否され、チェーンには決して届かない。</p>
      <p>検査を通った提案は投票にかけられる。賛成が十分に集まれば、あらかじめ決められたブロックで、すべてのノードに同時に法となる。管理者の鍵も、創設者の手元の非常スイッチもない。投票で否決されれば、何も変わらない。</p>
      <p>今年の初め、Tau チームのメンバーはこう率直に語った。統治はとても柔軟で、<i>「システムは望まれた仕様に従って自らを更新する」</i>。</p></div>
    </div>
    <div class="u s2 rl rt">
      <h3>なぜ投票だけでなく論理なのか</h3>
      <p class="ni">投票はばかげたものを通してしまうことがある。それぞれはもっともらしい二つのルールが、組み合わさるとあらゆるトランザクションを不可能にすることもある。Tau 言語は<i>決定可能</i>なので、新しいルールが古いルールと共存できるかどうかに、機械は必ず有限の時間で答えられる。投票は人々が何を望むかを決め、論理はそれが実現できることを確かめる。</p>
      <div class="ad"><div class="t">フォークにうんざり？</div><p>当世流の新しい手法<b>逐点改訂</b>をお試しあれ。プログラムが動いているそのときにルールが更新される。入れ直しも、更新窓口の行列も無用。</p><div class="fine">Tau チーム、2025 年 3 月に実演。</div></div>
    </div>
  </div>
</div>`,
/* ---------------- 4 静かな年月 + 追悼 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 4 面</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">工房便り：静かな 4 年と、ひとつの偉大な方程式</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">2019〜2022</div>
      <h2>地味な年月、難解な数学</h2>
      <div class="c2"><p class="dc ni">2019 年 5 月から月例の進捗報告が始まり、その内容は率直だった。古い動画はもう古い、とチームは言った。「新しい Tau はまったく違う」。仕事は TML（決定図の上に作られた論理言語）と、最小限の議論の場へと移っていた。</p>
      <p>すべての季節が順調だったわけではない。2019 年 9 月、取引所 OpenLedger は取引量の少なさから AGRS の上場を廃止し、チームはほかの取引の場を探し始めた。ビデオ相談アプリ Agoras Live は発表され、延期され、Tau Live と改名され、そして 2023 年 8 月、全員が中核に集中するために一時停止された。</p>
      <p>その間にも土台は固められていた。2020 年 8 月、Ohad Asor と Avishai Carmi 教授がホワイトペーパーを発表し、それがその後数年の仕事の指針となった。2021 年 8 月、Asor は任意のブール代数上のブール方程式系を解く完全な方法を見つけたと発表した。脚注のように読めるが、これが今日の Tau 言語の根である。</p>
      <p>2022 年 6 月、ウェブサイトは idni.org から tau.net へ移り、チームは道具としての TML と、新しい Tau 言語を切り分けた。後者は自らの文について、そして時間について語ることができる。自らのルールを記述できる言語こそ、チェーンがルールを安全に変えるために必要なものだ。</p></div>
      <div class="box"><p><b>投書より、2021 年 2 月。</b>Victor という読者が、Agoras の安全性にプルーフ・オブ・ステークは必要かと尋ねた。答えはこうだった。Tau がプルーフ・オブ・ステークで動くかどうかは<i>「利用者が決めることになる。だから合意は、利用者の望みに従って時とともに変わりうる」</i>。5 年半後、テストネット Alpha で、利用者はまさにそれを行った。<i>第 1 面参照。</i></p></div>
    </div>
    <div class="u s2 rl obit">
      <h3>追悼</h3>
      <p class="center small" style="text-indent:0"><i>本紙は、それぞれの務めを果たした以下の計画に敬意を表する。</i></p>
      <p><b>独立したプロジェクトとしての Zennet</b> 2014〜2015。共有スーパーコンピューター。Agoras に引き継がれ、その市場の一つとして生き続ける。</p>
      <p><b>Agoras Live、のちの Tau Live</b> 2020〜2023。暗号資産で支払うビデオ相談。中核を育てるため一時停止。</p>
      <p><b>土台としての TML</b> 2022 年まで。より有能な後継者、Tau 言語に席を譲る。</p>
      <p><b>基盤としての Qtum、Solana、Polkadot</b> 2023〜2024 年に検討され、丁重に辞退。Tau は自前のノードを築いた。</p>
      <p><b>Z3 ソルバー</b> 2025 年 7 月に引退、より身軽な CVC5 が後を継ぐ。</p>
      <p><b>言語のインターネット</b> 利用者が新しい言語を加えられるようにする計画。2026 年 8 月に眠りにつく：Tau 言語のほうがうまくやれる。</p>
      <p class="center small"><i>供花はご辞退申し上げます。代わりにノードの形でテストネットへどうぞ。</i></p>
    </div>
  </div>
</div>`,
/* ---------------- 5 言語 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 5 面</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">自らを語る言語、GitHub に放たれる</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">2023〜2024</div>
      <h2>Tau 言語 Alpha 版、一般公開</h2>
      <div class="deck">作者いわく、その最初の本当の実演はテストネットそのものになる</div>
      <div class="c2"><p class="dc ni">2024 年 11 月 15 日、Tau 言語は Alpha 版として GitHub で一般に公開された。風変わりな言語である。たいていのプログラミング言語はコンピューターに何をすべきかを指示する。Tau 言語は、いまそして今後のあらゆるステップで何が真でなければならないかを記述し、その方法はソルバーが見つけ出す。</p>
      <p>土台はその前年に据えられていた。2023 年 6 月、Tau 独自のチェーンの作業が始まった。目標は、ブロックチェーンのどの部分も論理で書かれ、新しいブロックごとに変えられることだった。2023 年 11 月、テストネットの計画が固まった。最小限から始め、何が有効なブロックかは利用者が定める。</p>
      <p>チームはまず Qtum の上に築くことを考え、2024 年には Solana、Aptos、Polkadot SDK を検討し、最終的に自前のノードを作ることにした。その間には、一意の利用者識別に関する仮特許、Tau のパーサーの公開、そして 2023 年 12 月の Nvidia Inception への参加もあった。</p>
      <p>2024 年 5 月、Asor は原子のないブール代数についての講義を 8 本収録した。この言語の下にある論理である。数学好きの読者は Tau のチャンネルで見つけられる。それ以外の読者には、テストネットのほうが親しみやすい入門であることをお伝えしておく。</p></div>
    </div>
    <div class="u s2 rl">
      <h3>論理学者に聞く</h3>
      <p class="ni"><b>問：</b>「決定可能」とはどういう意味で、なぜ気にすべきなのか。</p>
      <p class="ni"><b>答：</b>あなたのルールについての問いに、機械が必ずはいかいいえで答え、永遠に止まってしまうことがないという意味だ。だからこそ Tau のチェーンは、新しいルールを施行する前に、それを現行のすべてのルールと照らし合わせられる。毎回、必ず。</p>
      <p class="ni"><b>問：</b>では「自らを語る」とは。</p>
      <p class="ni"><b>答：</b>この言語は、自分自身の文を推論の対象として扱える。あるルールがほかのルールについてのものであってもよい。「ルールの変え方」についてのルールも含めて。</p>
      <div class="ad"><div class="t">Alpha 版 登場</div><p>TAU 言語。何が真でなければならないかを述べれば、道はソルバーが見つける。どなたでも無料。</p><div class="fine">github.com/IDNI/tau-lang</div></div>
    </div>
    <div class="u full rt">
      <div class="box"><h3>新式の立法文書の見本</h3>
        <div class="grid" style="grid-template-columns:3fr 2fr">
          <div class="u"><p class="ni wire" style="white-space:pre-line">always (
  o6[t] = i10[t]  &amp;&amp;
  o7[t] = { 1 }
)</p></div>
          <div class="u rl"><p class="ni small">テストネットの合意ルールの最小形から。読み方：<i>あらゆるステップで、ブロックが有効なのは署名の検証が通るときであり、かつそのときに限る。そして、権限のあるすべての提案者がブロックを生成できる。</i>投票でこの数行を変えれば、ネットワークの合意の仕方が変わる。</p></div>
        </div>
      </div>
    </div>
  </div>
</div>`,
/* ---------------- 6 2025 年の電報 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 6 面</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">12 か月、一つのネットワーク：工事現場からの電報</div>
  <div class="grid">
    <div class="u s3 wire">
      <div class="kick">特電 · 2025 年</div>
      <p><b>1 月</b> テストネットの中核ルール TAU の仕様として記述 ヲハリ テストネットの約 3 割が TAU 製 ヲハリ 同じ入力に同じ出力 ヲハリ</p>
      <p><b>3 月</b> 逐点改訂 成功 ヲハリ 動作中のプログラムが更新を受け取り次のステップに矛盾なく統合 ヲハリ 以後ルールはこうして変わる ヲハリ</p>
      <p><b>4 月</b> 米国特許 取得 ヲハリ ノードの設計 確定 ヲハリ ラッパーは入出力ストリームのみで TAU と通話 ヲハリ</p>
      <p><b>5 月</b> 全トランザクション TAU が裁定 ヲハリ 有効なものはメモリプールで待機 ヲハリ</p>
      <p><b>6 月</b> 12 の節目のロードマップ ヲハリ コンソールのウォレット ヲハリ 1 つのトランザクションでルールと送金を同時に運搬 ヲハリ</p>
      <p><b>7 月</b> ブロック 生成され保存 ヲハリ ハッシュで連結 マークルルート ヲハリ ソルバー Z3 から CVC5 へ ヲハリ</p>
    </div>
    <div class="u s3 rl wire">
      <div class="kick">続き</div>
      <p><b>8 月</b> ノード 起動時に履歴から状態を再構築 ヲハリ 任意のビット幅の数値 ヲハリ</p>
      <p><b>9 月</b> LIBP2P でピアツーピア接続 ヲハリ アンドロイドのウォレット TAU のルールを送信可 ヲハリ</p>
      <p><b>10 月</b> 単一ノードからネットワークへ ヲハリ TAU プロトコル 6 種 ヲハリ 同期は ハンドシェイク ヘッダー ブロック 状態 の順 続いてゴシップ ヲハリ</p>
      <p><b>11 月</b> テストネットのコード 一般公開 ヲハリ リポジトリ TAU-TESTNET ヲハリ ノードは身元を保持 ヲハリ</p>
      <p><b>12 月</b> 初のプルーフ・オブ・オーソリティのブロック ヲハリ BLS 署名 ヲハリ 各ブロックに状態ハッシュの署名 ヲハリ 新年おめでたう ヲハリ</p>
      <p class="center" style="margin-top:.8em">· · ·</p>
    </div>
    <div class="u s4 rt">
      <h2 class="l">すべてを可能にした秘訣</h2>
      <div class="c2"><p class="ni dc">この年の電報のうち、額に入れて飾るべきは 3 月のものだ。逐点改訂とは一つの方法である。動いている Tau のプログラムが更新の流れを受け取り、そこに書かれたことを次のステップのプログラムへ矛盾なく取り込む。</p>
      <p>走行中に時刻表を改められる列車を思い浮かべてほしい。次の駅に着くころには、もう新しい時刻表で走っている。停車も、造り直しもなく、二両の客車がそれぞれ別の時刻表で走ることもない。それが Tau でのルール変更だ。</p>
      <p>2025 年の残りの仕事は、この列車のための線路を敷くことだった。トランザクション、ブロック、保存、ネットワーク、署名。12 月には、各部分が公開のネットワークの上でそろって動いていた。</p></div>
    </div>
    <div class="u s2 rl rt">
      <figure class="photo"><img src="img/hud-core.jpg" width="700" height="574" style="height:auto;aspect-ratio:700/574" alt="Tau HUD のチェーンコアの網点写真"><figcaption><b>夜の中核。</b>生成されたブロックが中央で光り、バリデーターとノードが輪に沿って巡る。Tau HUD にて撮影。</figcaption></figure>
    </div>
  </div>
</div>`,
/* ---------------- 7 2026 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 7 面</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">利用者がハンドルを握った年</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">2026 · 年代記</div>
      <h2>「実演」から、プログラムできるお金へ</h2>
      <div class="c2"><p class="dc ni">1 月は約束を果たすことから始まった。すべてのブロックが、自らが従ったルールの正確なスナップショットを記録するようになり、新しく加わるノードは全履歴を再生する代わりに状態ハッシュを照合できるようになった。2 月、チームはこの年の標語を定めた。テストネット Alpha <i>こそが</i>実演である。</p>
      <p>4 月にはフォークの選択と再編成、ただ一つの正規のチェーン、そして組み込みの検査と並ぶ利用者定義のポリシー検査が加わった。5 月、決定的な一歩が踏み出された。合意が Python から Tau のロジックへ移され、利用者がルールでそれを変えられるようになった。同時に、ノード、鍵、投票を扱う開発者向けのコマンドラインも登場した。</p>
      <p>8 月、利用者は本当にそれを変えた。投票で固定のバリデーターリストからプルーフ・オブ・ステークへ切り替え、そしてまた戻した。どのノードも再配置せずに。バリデーターリストそのものも、いまでは Tau のロジックの中にある。</p>
      <p>9 月、製品の段階が宣言された。ルールのテンプレートと共有機能を備えたシンプルなウォレットモードで、さらに 2 件の特許も取得した。10 月には共同署名付きの送金が登場した。大きな支払いには複数の承認が必要で、期限はどんな時計にも偽れないブロック数で数える。よく使われる仕様の読み込みは 68 秒から 2.4 秒になった。</p>
      <p>メインネットと Agoras は、いまもチームのロードマップ上の計画である。珍しいことに、今回はその道が見えている。</p></div>
    </div>
    <div class="u s2 rl">
      <h3>ふだんの言葉で、記録はチェーンに</h3>
      <p class="ni">7 月に披露されたウォレットの作成モードでは、利用者がルールを日常の英語で説明する。エージェントがそれを Tau で書き、利用者が署名し、ほかのルールと同じように提案され、受け入れられる。</p>
      <div class="q">「ふだんの英語で言ったことを Tau 言語に変える。あとは Tau がやってくれる。」<small>Tau チーム、2026 年 7 月の質疑応答</small></div>
    </div>
    <div class="u full rt">
      <div class="kick">科学</div>
      <h2>投票所の機械</h2>
      <div class="c3"><p class="ni dc">6 月、テストネットは風変わりな試験を受けた。チームの言葉によれば、彼らは<i>「それぞれが独自の身元、ガードレール、目標を持つエージェントの群れを丸ごと」</i>用意し、利用者として、またバリデーターとしてネットワーク上で活動させた。</p>
      <p>エージェントたちはルールを提案し、ルールに投票し、互いに送金した。できるかぎり本物に近い形で。ガードエージェントが、提案が先へ進む前にそれを審査した。</p>
      <p>結果は二つあった。ネットワークは負荷に耐えた。そして統治に説明責任が生まれた。チェーン上のどのルールも、いまでは誰が提案し、どのように承認されたかまでたどれる。</p>
      <p>これは、Tau が最初から目指してきたものを垣間見せる。人々と、人々のために働く機械が、検査できる言語で自分の望みを述べる場所である。</p>
      <p>将来の投票者が男でも女でも機械でも、規則集は一冊、チェーンは一本である。</p></div>
    </div>
  </div>
</div>`,
/* ---------------- 8 公民の授業 + 投書 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 8 面</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">Tau で法はどうつくられるか</div>
  <div class="grid">
    <div class="u full diag">
      <svg viewBox="0 0 760 150" aria-label="提案、検査、合意、施行">
        <defs><marker id="ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="#1b1813"/></marker></defs>
        <g font-size="14" text-anchor="middle">
          <circle cx="80" cy="56" r="40" fill="none" stroke="#1b1813" stroke-width="1.6"/><text x="80" y="52" font-size="26" font-weight="700">壱</text><text x="80" y="74" font-size="13">提案</text>
          <circle cx="280" cy="56" r="40" fill="none" stroke="#1b1813" stroke-width="1.6"/><text x="280" y="52" font-size="26" font-weight="700">弐</text><text x="280" y="74" font-size="13">検査</text>
          <circle cx="480" cy="56" r="40" fill="none" stroke="#1b1813" stroke-width="1.6"/><text x="480" y="52" font-size="26" font-weight="700">参</text><text x="480" y="74" font-size="13">合意</text>
          <circle cx="680" cy="56" r="40" fill="#1b1813"/><text x="680" y="52" font-size="26" font-weight="700" fill="#efe5cf">四</text><text x="680" y="74" font-size="13" fill="#efe5cf">施行</text>
          <line x1="124" y1="56" x2="234" y2="56" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar2)"/><line x1="324" y1="56" x2="434" y2="56" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar2)"/><line x1="524" y1="56" x2="634" y2="56" stroke="#1b1813" stroke-width="1.5" marker-end="url(#ar2)"/>
          <text x="80" y="118" font-size="13">Tau でルールを書き、</text><text x="80" y="134" font-size="13">トランザクションで送る</text>
          <text x="280" y="118" font-size="13">現行の法とともにコンパイル。</text><text x="280" y="134" font-size="13">矛盾すれば退場</text>
          <text x="480" y="118" font-size="13">利用者が投票し、</text><text x="480" y="134" font-size="13">賛成が十分なら可決</text>
          <text x="680" y="118" font-size="13">決めておいたブロックで</text><text x="680" y="134" font-size="13">全ノードに施行</text>
        </g>
      </svg>
    </div>
    <div class="u full rt"><div class="kick">通信</div><h2>読者からの投書</h2><p class="center small" style="text-indent:0"><i>読者が Tau チームの月例質疑応答に寄せた質問と、チームの回答から。一部省略。</i></p></div>
    <div class="u s3">
      <p class="ni"><b>編集部御中：</b>チェーン上の統治は非公開ですか。ネットワークの運営に信頼できる第三者は必要ですか。<i>Levan</i></p>
      <p class="ni small"><b>回答：</b>最初は非公開ではないが、利用者が望めば非公開にできる。信頼できる第三者は必要ない。「統治はとても柔軟で、利用者はシステムがどう動くべきかを定められ、システムは自らを更新する。」<i>（2026 年 1 月）</i></p>
      <hr class="rule2">
      <p class="ni"><b>編集部御中：</b>Tau のブロックチェーンは単一のグローバルなアカウント状態でなければなりませんか。それとも、より拡張性の高いシャーディングのモデルも使えますか。<i>Phillip</i></p>
      <p class="ni small"><b>回答：</b>「まずはグローバルなアカウント状態から始めるが、原則として、利用者がそれを変えることに何の問題もないはずだ。」<i>（2026 年 1 月）</i></p>
    </div>
    <div class="u s3 rl">
      <p class="ni"><b>編集部御中：</b>いまの作業は構想の限られた一部にすぎないのですか。メインネットまでに何が残っていますか。<i>Kurosawa</i></p>
      <p class="ni small"><b>回答：</b>「中核の構想はすでに Tau 言語で実現されている。ブロックチェーンでも。もちろん改善すべきことはたくさんあるが、もうそこにあり、もう動いている。」<i>（2026 年 8 月）</i></p>
      <hr class="rule2">
      <p class="ni"><b>編集部御中：</b>Tau 言語が、テーブルと算術を備え、本物の開発者が使える 1.0 版になるのはいつですか。<i>Kudo Sara</i></p>
      <p class="ni small"><b>回答：</b>中核の機能はほぼそろい、算術はすでに入った。次は完全な時相論理の量化子、その次がテーブル。<i>（2026 年 7 月）</i></p>
    </div>
    <div class="u s2 rt">
      <p class="ni"><b>編集部御中：</b>Tau のようなシステムで検閲は起こりえますか。<i>Bobby</i></p>
      <p class="ni small"><b>回答：</b>「利用者が何かを起こすと決めたなら、それは起こる。それこそが肝心な点だ。」<i>（2023 年 1 月）</i></p>
    </div>
    <div class="u s2 rl rt">
      <p class="ni"><b>編集部御中：</b>新聞は量子コンピューターが鍵を破るという話でもちきりです。Tau はどう備えますか。<i>Agoras Tau</i></p>
      <p class="ni small"><b>回答：</b>短期的にはアドレスと鍵を使い回さないこと。長期的には署名を耐量子方式へ移すこと。<i>（2026 年 6 月）</i></p>
    </div>
    <div class="u s2 rl rt">
      <p class="ni"><b>編集部御中：</b>Tau は AI エージェントのネットワークの通信層になれますか。<i>Smick</i></p>
      <p class="ni small"><b>回答：</b>なれる。「ただし、おしゃべりを運ぶ電線としてではなく、何が真で何が許されるかについてエージェントたちが合意する層として。」<i>（2026 年 6 月）</i></p>
    </div>
  </div>
</div>`,
/* ---------------- 9 今日 + 案内広告 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 9 面</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">今日のテストネット</div>
  <div class="grid">
    <div class="u s4">
      <div class="kick">ノード駐在記者</div>
      <h2>見物人すべてに開かれた、公開のチェーン</h2>
      <div class="c2"><p class="dc ni">テストネット Alpha は公開で動いており、本紙の記者は傍聴席に一席を得ている。Tau HUD は、Tau を手がける会社 IDNI のブートノードの隣で自前のノードを動かし、見たものを紙面に載せている。</p>
      <p>現在は IDNI が運営するただ一人のバリデーターが、およそ 8 秒に一つずつすべてのブロックを生成している。利用者はトランザクションの形でルール変更を提案し、提案は票を集め、合意されると施行のブロックを待つ。HUD はそれを前もって示し、カウントダウンし、施行の瞬間に輪を灯す。</p>
      <p>静かな時間には、同じプロトコルに従うシミュレーションもあり、毎時一つの出来事と、1 日 2 回の合意の切り替えを用意している。それが現れる場所はすべて琥珀色で示され、誰もリハーサルを本番と取り違えないようにしてある。</p>
      <div class="box wire"><p class="ni" id="wire1">{{WIRE}}</p></div></div>
    </div>
    <div class="u s2 rl">
      <h3>見どころ案内</h3>
      <div class="watch">
        <p><a href="/?lang=ja" data-noflip>チェーンコア、ライブ</a> <i>tauhud.com</i></p>
        <p><a href="/proposals/" data-noflip>ルール変更と投票</a> <i>/proposals</i></p>
        <p><a href="/explorer/" data-noflip>すべてのブロックとトランザクション</a> <i>/explorer</i></p>
        <p><a href="/history/" data-noflip>ブロックごとのタイムトラベル</a> <i>/history</i></p>
        <p><a href="/playground/" data-noflip>自分でルールを書く</a> <i>/playground</i></p>
        <p><a href="/chronicle/" data-noflip>年代記の全編</a> <i>/chronicle</i></p>
      </div>
      <div class="ad inv"><div class="t">電報サービス</div><p>合意されたルール変更、施行、新しいノードのすべてを、起きたその瞬間にあなたのポケットへ。</p><p><a href="https://t.me/tauHUDcom" target="_blank" rel="noopener" data-noflip>t.me/tauHUDcom</a></p></div>
    </div>
    <div class="u full rt"><h3 style="text-align:left;border-bottom:1px solid;padding-bottom:.2em">案内広告</h3></div>
    <div class="u s2 cls">
      <p><b>求人。</b>着実な性分のノード運用者を求む。Tau のノードを動かせば、30 分以内に本紙の軌道に登場。キットと説明は <a href="/nodes/" data-noflip>tauhud.com/nodes</a> にて。</p>
      <p><b>求職。</b>バリデーター。時間厳守、すべてのブロックに署名。席を求む。ネットワークが合意したルールにはすべて従います。</p>
    </div>
    <div class="u s2 rl cls">
      <p><b>落とし物。</b>ハードフォーク一つ。惜しむ者なし。拾った方はそのままお持ちください。</p>
      <p><b>お知らせ。</b>テストネットの AGRS に価値はありません。テストネットを試すためだけのもので、本紙は提供も販売もしていません。</p>
      <p><b>好奇心旺盛な方へ。</b><a href="/playground/" data-noflip>プレイグラウンド</a>でルールを提出し、チェーンがそれを受け入れるか拒むかを安全に見物できます。</p>
    </div>
    <div class="u s2 rl cls">
      <p><b>尋ね人。</b>フォーラムのメンバー HunterMinerCrafter 殿：あなたが 2014 年に語った考えは遠くまで来ました。今日動いているのは別の設計ですが、始まりはあの議論でした。どうぞ見にいらしてください。</p>
      <p><b>作り手の皆様へ。</b>テストネットのコードは公開されています。チームには GitHub で連絡できます。10 月だけで、コミュニティからのプルリクエストが 4 件マージされました。</p>
    </div>
    <div class="u full rt"><div class="box"><div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
      <div class="u"><h3>暦</h3><p class="ni small">1 ブロック 8 秒とすれば、テストネットは 1 時間におよそ 450 ブロック、1 日におよそ 10,800 ブロックを生成する。今日合意されたルールはたいてい数ブロック先で施行されるよう決められるので、誰もが時刻を前もって知ることができる。</p></div>
      <div class="u rl"><h3>リハーサルの時刻表</h3><p class="ni small">シミュレーションでは、毎時 20 分に特別なルール変更が提案され、30 分に施行される。合意は UTC 10:30 にプルーフ・オブ・ステークへ切り替わり、UTC 16:30 に固定のリストへ戻る。リハーサルは深夜 0 時に最初からやり直す。</p></div>
      <div class="u rl"><h3>読者へのご注意</h3><p class="ni small">Tau HUD は非公式のコミュニティプロジェクトで、IDNI とは無関係である。公開テストネットを読み取り、見たものを報じている。両者が食い違うときは、チェーンが正しく本紙が誤っている。</p></div>
    </div></div></div>
  </div>
</div>`,
/* ---------------- 10 娯楽 ---------------- */
`<div class="pg">
  <div class="rh"><span>第 10 面</span><span class="nm">{{NAME}}</span><span>{{DATE}}</span></div>
  <div class="banner sm">論理好きのための気晴らし</div>
  <div class="grid">
    <div class="u s3">
      <h3>三人のバリデーターの謎</h3>
      <p class="ni">あるチェーンでは、ルール変更に三人のバリデーターの<i>過半数</i>の合意が要る。Ada は賛成。Cleo はいつも Ada と同じ票を投じる。Bram は信条として、いつも Cleo と反対の票を投じる。変更は通るか。</p>
      <div class="ups"><p><b>答え：</b>通る。Ada と Cleo が賛成、Bram が反対で、3 票中 2 票の過半数。Bram には別の信条を探すことをおすすめする。</p></div>
    </div>
    <div class="u s3 rl">
      <h3>矛盾コーナー</h3>
      <p class="ni">同じ日に三つの提案が Tau のチェーンに届いた。入口で拒否されるのはどれか。</p>
      <p class="ni small">（甲）1,000 AGRS を超える送金には署名が二つ要る。<br>（乙）基本手数料は常に 6。<br>（丙）（乙）が施行されている間、基本手数料は常に 7。</p>
      <div class="ups"><p><b>答え：</b>（丙）。（乙）と矛盾するので、どんな投票よりも前に、コンパイル時の検査で拒否される。（甲）と（乙）は共存できる。</p></div>
    </div>
    <div class="u full rt gl"><h3 style="text-align:left">新しい読者のための用語集</h3>
      <div class="c3"><p><b>Agoras。</b>IDNI がいずれ Tau の上に築く計画の市場。テストネットでは、AGRS は価値のない試験用の単位にすぎない。</p>
      <p><b>ブロック。</b>チェーンの帳簿の、封をされた 1 ページ。Tau では、各ブロックが自らの従ったルールを記録する。</p>
      <p><b>ブートノード。</b>新しいノードがネットワークの残りを見つけるために使う、最初のノード。</p>
      <p><b>合意。</b>誰がブロックを生成でき、それがいつ有効と数えられるかのルール。Tau では、これ自体も一つのルールである。</p>
      <p><b>ハードフォーク。</b>新しいソフトウェアによるルール変更。誰かが拒めば、チェーンは割れる。</p>
      <p><b>メモリプール。</b>まだブロックに入っていないトランザクションの待合室。</p>
      <p><b>逐点改訂。</b>ルールの更新を、動いているプログラムの次のステップへ取り込むこと。</p>
      <p><b>提案。</b>トランザクションとして送られるルール変更で、検査と投票を待つもの。</p>
      <p><b>バリデーター。</b>ブロックの生成と提案への投票を任されたノード。</p></div>
    </div>
    <div class="u s4 rt">
      <h2 class="l">近日予告</h2>
      <div class="c2"><p class="ni dc">チームが発表した今後の演目：言語へのテーブルと抽象データ型の追加、次のリリース前の開発ブランチのマージ、ふだんの言葉でルールを書けるシンプルなウォレット、そしてさらに先には、メインネットと、チームが長く描いてきた計算能力・知識・専門家の助言の市場、Agoras。</p>
      <p>本紙は日付を約束できないし、チームも約束しない。だが本紙はこれだけは約束できる。テストネット Alpha で次にルールが変わるとき、Tau HUD はその場にいる。あなたもいられる。</p></div>
      <div class="coupon"><div class="t">切り抜いて保存</div><p>ライブで見る：<b>tauhud.com</b> · 通知：<b>t.me/tauHUDcom</b> · ルールを試す：<b>tauhud.com/playground</b> · Tau 公式：<b>tau.net</b></p></div>
    </div>
    <div class="u s2 rl rt">
      <div class="ad"><div class="t">Tau HUD</div><p>自らのルールを変えるチェーンを見るための 12 の計器。無料。オープンソース。</p><div class="fine">時間と道具と、質素なサーバー一台で動いています。</div></div>
      <div class="box small notice" style="margin-top:.6em"><p class="ni"><b>読者へのお知らせ。</b>『{{NAME}}』は、コミュニティプロジェクト Tau HUD がつくる親しみやすい非公式の新聞で、IDNI とは無関係です。情報と楽しみのために書かれたもので、投資の助言ではなく、紙面で売っているものは何もありません。テストネットの AGRS は練習用で、価値はありません。ここで語られる計画は IDNI 自身の発言を伝えたもので、変わることがあります。事実は Tau チームが公開した動画、記事、論文から取りました。字幕からの引用は少し整えてあります。本紙は善意で編集していますが、実験的な試みであり、誤りもありえます。大事なことは元の出典をご確認ください。パズルと天気はお楽しみのためだけのものです。</p></div>
    </div>
  </div>
</div>`
  ]
};
