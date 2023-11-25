import os
import re
import sys
import fitz
import asyncio
import pandas as pd
from collections import deque
from httpx import ReadTimeout
from openai import AsyncClient

# MODEL = 'gpt-3.5-turbo-1106'
MODEL = 'gpt-4-1106-preview'
client = AsyncClient(timeout=10.0)
docs_inpath = 'pdfs'
docs_outpath = 'pdfs_out'
para_group_size = 40
code_pattern = re.compile('``` ?[Pp]ython\n(?:(?!```)[\S\s])+\n```')


def cleanup_python_response(response):
    response = response.strip('` \n')
    if response.lower().startswith('python'):
        response = response[6:].lstrip()
    return response


async def main():
    all_splitted_sections = []
    os.makedirs(docs_outpath, exist_ok=True)
    all_doc_outpath = os.path.join(docs_outpath, 'combined.csv')
    for root, _, files in os.walk(docs_inpath):
        for file in files:
            doc_inpath = os.path.join(root, file)
            outfile = f'{os.path.splitext(file)[0]}.csv'
            outdir = os.path.join(docs_outpath, os.path.relpath(root, docs_inpath))
            os.makedirs(outdir, exist_ok=True)
            doc_outpath = os.path.join(outdir, outfile)
            paras = deque(maxlen=para_group_size)
            page_nums = deque(maxlen=para_group_size)
            sections = {}
            splitted_sections = []
            all_paras = [[block[4], page.number + 1] for page in fitz.open(doc_inpath) for block in page.get_text('blocks')]
            num_paras = len(all_paras)
            j = 0
            for i, (para, page_num) in enumerate(all_paras):
                text = para.strip()
                if text:
                    marker = f'【{j}†source】'
                    j += 1
                    sections[marker] = text
                    paras.append(f'{marker} {text}')
                    page_nums.append(page_num)
                    if i == num_paras - 1 or len(paras) == para_group_size:  # End of doc or group big enough to process
                        excerpt = '\n'.join(paras)
                        print(f'Excerpt:\n{excerpt}\n')
                        response = []
                        while True:
                            try:
                                completion = await client.chat.completions.create(
                                    messages=[
                                        {
                                            'role': 'user',
                                            'content': f'{excerpt}\n\nIntructions: Split the text excerpt above into sections based on the content and give me the list of section markers in the form "[\'【i†source】\', \'【j†source】\', ...]" where i, j are selected such that the corresponding markers indicate the start of a new section, not just a new paragraph. Thus, non-qualifying markers should be ignored. Put the sections into a Python list named "sections" inside a Python code block. Start by specifying the code block as Python code block.'
                                        }
                                    ],
                                    model=MODEL,
                                    temperature=0.0,
                                    stream=True
                                )
                                async for chunk in completion:
                                    part = chunk.choices[0].delta
                                    if part.content is not None:
                                        sys.stdout.write(part.content)
                                        sys.stdout.flush()
                                        response.append(part.content)
                                sys.stdout.write('\n')
                                sys.stdout.flush()
                                response = ''.join(response)
                                break
                            except ReadTimeout:
                                pass
                        code_segments = code_pattern.findall(response)
                        for code_segment in code_segments:
                            code_segment = cleanup_python_response(code_segment)
                            if code_segment.startswith('sections'):
                                print(f'Code: {code_segment}')
                                section_markers = eval(code_segment[8:].lstrip()[1:].lstrip())
                                print(f'Sections: {section_markers}')
                        section_marker_iter = iter(section_markers)
                        curr_section_marker = next(section_marker_iter)
                        curr_section_list = []
                        to_delete_markers = []
                        text_len = 0
                        try:
                            for marker, content in list(sections.items()):
                                if marker == curr_section_marker:
                                    if curr_section_list and text_len > 128:
                                        splitted_sections.append(f'【{len(splitted_sections)}†source】 ' + '\n'.join(curr_section_list))
                                        all_splitted_sections.append([file, f'【{len(all_splitted_sections)}†source】', '\n'.join(curr_section_list), page_nums[0]])
                                        # all_splitted_sections.append(f'【{len(all_splitted_sections)}†source】 ' + '\n'.join(curr_section_list))
                                        curr_section_list.clear()
                                        text_len = 0
                                        for m in to_delete_markers:
                                            del sections[m]
                                            paras.popleft()
                                            page_nums.popleft()
                                        to_delete_markers.clear()
                                    curr_section_marker = next(section_marker_iter)
                                text_len += len(content)
                                curr_section_list.append(content)
                                to_delete_markers.append(marker)
                        except StopIteration:
                            pass
            if sections:
                if splitted_sections:
                    splitted_sections[-1] = '\n'.join([splitted_sections[-1], *sections.values()])
                    all_splitted_sections[-1][2] = '\n'.join([all_splitted_sections[-1][2], *sections.values()])
                else:
                    splitted_sections.append(f'【{len(splitted_sections)}†source】 ' + '\n'.join(sections.values()))
                    all_splitted_sections.append([file, f'【{len(all_splitted_sections)}†source】', '\n'.join(sections.values()), page_nums[0]])
            pd.DataFrame.from_records([[section] for section in splitted_sections]).to_csv(doc_outpath, index=None)
    pd.DataFrame.from_records(all_splitted_sections, index=None, columns=['documentTitle', 'referenceMarker', 'content', 'pageNumber']).to_csv(all_doc_outpath, index=None)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
