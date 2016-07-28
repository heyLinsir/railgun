<code>Splay Tree</code>是平衡二叉搜索树的一种重要形式，而且操作高效，代码简洁。

为了能够提高<code>Splay Tree</code>的分摊效率，我们将采用双层伸展的方法。请你设计白盒测试用例，来测试<code>Splay Tree</code>的伸展调整算法，为了简化难度，我们只测试该算法中的第一重循环。

我们将该测试算法的第一重循环的代码已经写入附件中，并且附上了二叉树节点类**BinNode**， **BinNode**类的代码也已添加至附件中。

观察附件中splay.py 中的函数 <code>splay</code>，写白盒单元测试，以达到尽可能高的覆盖率。

注意在 Python 中单元测试的类型必须继承自 <code>unittest.TestCase</code>，并且以保存在 test_*.py 的文件中。

上交的代码必须符合相应语言的代码规范。请务必在截止日期前上交作业，否则有相应的评分折扣。