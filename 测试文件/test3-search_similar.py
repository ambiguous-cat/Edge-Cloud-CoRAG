#
# from initialize import add_document_to_knowledge
#
# add_document_to_knowledge("mos","这是一个测试文档，用于验证本地知识库的添加功能。")

from search_similar_documents import DocumentSearcher


query_text = "这是一个测试文档，用于验证本地知识库的添加功能。"
top_k = 5

searcher = DocumentSearcher()
results = searcher.search_similar_documents(query_text, top_k=top_k)

if results:
    for result in results:
        print(f"排名: {result['rank']}")
        print(f"片段ID: {result['chunk_id']}")
        print(f"所属文档ID: {result['doc_id']}")
        print(f"文档标题: {result['title']}")
        print(f"片段序号: {result['chunk_index']}")
        print(f"内容: {result['content']}")
        print(f"相似度: {result['similarity_score']:.4f}")
        print('-' * 50)
else:
    print("未找到相似文档")
print(results)
searcher.close()