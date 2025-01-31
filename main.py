import numpy as np
import pandas as pd
import os
import re,ast
import time
import multiprocessing as mp
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import warnings
warnings.filterwarnings('ignore')
from statsmodels.formula.api import ols

'''read datasets'''

datasets_path=''
tx=pd.read_csv(datasets_path+"/transactions_data.csv")
input_data=pd.read_csv(datasets_path+"/input_data.csv")
output_data=pd.read_csv(datasets_path+"/output_data.csv")
ad_info=pd.read_csv(datasets_path+"/address_info.csv")
tx_list=tx['tx_hash'].tolist() #tx_hash만을 리스트

# Address Script Type Processing
def address_script(input_data, output_data):
    # 입력 데이터와 출력 데이터의 주소 해시를 중복을 제거하고 리스트로 만듭니다.
    ad_list = list(set(input_data['address_hash'].tolist() + output_data['address_hash'].tolist()))

    # 각 주소의 유형을 판별하여 script_type 리스트에 저장합니다.
    script_type = []
    for ad in ad_list:
        if ad[0] == '1':
            script_type.append('P2PKH')  # 주소 해시의 첫 번째 문자가 '1'인 경우 P2PKH 타입입니다.
        elif ad[0] == '3':
            script_type.append('P2SH')  # 주소 해시의 첫 번째 문자가 '3'인 경우 P2SH 타입입니다.
        elif ad[:3] == 'bc1':
            script_type.append('Bech32')  # 주소 해시의 처음 세 글자가 'bc1'인 경우 Bech32 타입입니다.
        else:
            script_type.append('Address which cannot be parsed')  # 이외의 경우 주소 해시를 해석할 수 없습니다.

    # 주소 해시와 script_type으로 데이터프레임을 생성합니다.
    ad_dataset = pd.DataFrame({'address_hash': ad_list, 'script_type': script_type})

    # 주소 해시와 script_type을 짝지어주는 사전인 ad_script_dic을 생성합니다.
    ad_script_dic = {ad_list[i]: script_type[i] for i in range(len(ad_list))}

    # 입력 데이터와 ad_dataset을 주소 해시를 기준으로 합칩니다.
    input_data = pd.merge(input_data, ad_dataset, on='address_hash', how='left')
    output_data = pd.merge(output_data, ad_dataset, on='address_hash', how='left')

    # script_type이 결측치인 행을 제거합니다.
    input_data.dropna(axis=0, subset=['script_type'], inplace=True)
    output_data.dropna(axis=0, subset=['script_type'], inplace=True)

    return input_data, output_data, ad_script_dic

input_data, output_data, ad_script_dic = address_script(input_data, output_data)
'''이 함수는 입력 데이터와 출력 데이터에 있는 주소 해시를 분석하여 해당 주소의 유형을 판별하고, 결과를 데이터프레임으로 반환합니다.'''


'''Identify change address'''

def change_address_identify(tx, input_data, output_data, ad_info, tx_list, ad_script_dic):
    start_time = time.time()
    h2 = []  # H2 값을 저장할 리스트
    h3 = []  # H3 값을 저장할 리스트
    h4 = []  # H4 값을 저장할 리스트
    h5 = []  # H5 값을 저장할 리스트
    h6 = []  # H6 값을 저장할 리스트
    condition1 = []  # Condition1 값을 저장할 리스트
    condition2 = []  # Condition2 값을 저장할 리스트
    condition3 = []  # Condition3 값을 저장할 리스트
    h7 = []  # H7 값을 저장할 리스트
    tx_type = []  # 트랜잭션 타입을 저장할 리스트
    k = 0

    for t in tx_list:
        t_info = tx[tx['tx_hash'] == t] 
        input_count = t_info['input_count'].values[0]  # 트랜잭션의 입력 개수
        output_count = t_info['output_count'].values[0]  # 트랜잭션의 출력 개수
        tx_input = input_data[input_data['tx_hash'] == t]  # 트랜잭션의 입력 데이터
        input_address = tx_input['address_hash'].tolist()  # 입력 주소의 리스트


        '''트랜잭션 타입 판별'''
    if input_count == 0:
        tx_type.append('Invalid input')  # 입력이 없는 경우
    elif output_count == 0:
        tx_type.append('Invalid output')  # 출력이 없는 경우
    elif output_count == 1:
        tx_type.append('Single-output')  # 출력이 하나인 경우
    elif input_count == 1:
        if output_count == 2:
            tx_type.append('Single-input 2-output')  # 입력이 하나이고 출력이 두 개인 경우
        else:
            tx_type.append('Single-input multiple-output')  # 입력이 하나이고 출력이 여러 개인 경우
    elif output_count == 2:
        tx_type.append('Multi-input 2-output')  # 입력이 여러 개이고 출력이 두 개인 경우
    else:
        tx_type.append('Multiple-input multiple-output')  # 입력이 여러 개이고 출력이 여러 개인 경우

    if output_count > 1:
        tx_output = output_data[output_data['tx_hash'] == t]  # 트랜잭션의 출력 데이터
        t_time = t_info['tx_time'].values[0]  # 트랜잭션의 시간
        input_script = tx_input['script_type'].tolist()  # 입력 스크립트 타입의 리스트
        output_script = tx_output['script_type'].tolist()  # 출력 스크립트 타입의 리스트
        input_sending = tx_input['address_value'].tolist()  # 입력 주소의 전송량 리스트
        output_address = tx_output['address_hash'].tolist()  # 출력 주소의 리스트
        output_receive = tx_output['address_value'].tolist()  # 출력 주소의 수신량 리스트
        output_receive_usd = tx_output['value_usd'].tolist()  # 출력 주소의 수신량 (USD) 리스트
        output_dict = {output_address[k]: output_receive[k] for k in range(len(output_address))}  # 출력 주소 및 수신량을 담은 딕셔너리
        output_dict_usd = {output_address[k]: output_receive_usd[k] for k in range(len(output_address))}  # 출력 주소 및 수신량 (USD)을 담은 딕셔너리
        '''트랜잭션 타입을 판별하는 부분과 출력 관련 정보를 수집하는 부분에 대한 주석입니다.'''

        '''H2'''
        self_change_tx = []  # 자체 변경 트랜잭션을 담을 리스트
        ad_h2 = []  # H2에 해당하는 주소를 담을 리스트

        # 출력 주소마다 처리
        for ad in output_address:
            if ad in input_address:
                self_change_tx.append('self-change')  # output_address에 있는 주소가 input_address에도 있으면 self-change
                break
            else:
                first_receive_time = ad_info[ad_info['address_hash'] == ad]['first_seen_receiving'].values[0]  # first_seen_receiving 시간 저장
                if t_time == first_receive_time:
                    ad_h2.append(ad)  # H2에 해당하는 주소를 ad_h2 리스트에 추가

        if self_change_tx != [] and self_change_tx[0] == 'self-change':
            h2.append('self-change')  # 자체 변경 트랜잭션이 있는 경우 H2에 self-change 추가
        elif len(ad_h2) == 0:
            h2.append('There is no new address')  # 새로운 주소가 없는 경우 H2에 "There is no new address" 추가
        elif len(ad_h2) == 1:
            h2.append(ad_h2[0])  # H2에 해당하는 주소가 하나인 경우 그 주소를 추가
        else:
            h2.append('There are multiple new addresses')  # H2에 해당하는 주소가 여러 개인 경우 "There are multiple new addresses" 추가


        '''H3'''
        ad_h3 = []  # H3에 해당하는 주소를 담을 리스트

        if self_change_tx != [] and self_change_tx[0] == 'self-change':
            h3.append('self-change')  # 자체 변경 트랜잭션이 있는 경우 H3에 self-change 추가
        elif len(ad_h2) == 0:
            h3.append('There is no new address')  # 새로운 주소가 없는 경우 H3에 "There is no new address" 추가
        else:
            for ad in output_address:
                if ad_info[ad_info['address_hash'] == ad]['output_count'].values[0] == 1:  # 주소가 새 주소이고 다시 사용되지 않았습니다
                    ad_h3.append(ad)  # H3에 해당하는 주소를 ad_h3 리스트에 추가

            if len(ad_h3) == 0:
                h3.append('All new addresses are reused')  # 모든 새 주소가 재사용된 경우 H3에 "All new addresses are reused" 추가
            elif len(ad_h3) == 1:
                h3.append(ad_h3[0])  # H3에 해당하는 주소가 하나인 경우 그 주소를 추가
            else:
                h3.append('Multiple new addresses exist that have not been reused')  # 재사용되지 않은 여러 개의 새 주소가 있는 경우 H3에 "Multiple new addresses exist that have not been reused" 추가

        '''H4'''
        ad_h4 = []  # H4에 해당하는 주소를 담을 리스트

        if len(set(input_script)) == 1:  # 입력 스크립트 유형이 하나인 경우
            if len(set(output_script)) > 1:  # 출력 스크립트 유형이 여러 개인 경우
                input_script_type = input_script[0]  # 입력 스크립트의 유형 저장
                for ad in output_address:
                    if ad_script_dic[ad] == input_script_type:  # 출력 주소의 스크립트 유형이 입력 스크립트 유형과 동일한 경우
                        ad_h4.append(ad)  # H4에 해당하는 주소를 ad_h4 리스트에 추가

                if len(ad_h4) == 1:
                    h4.append(ad_h4[0])  # H4에 해당하는 주소가 하나인 경우 그 주소를 추가
                elif len(ad_h4) == 0:
                    h4.append('No output of the same type as the input script')  # 입력 스크립트와 동일한 유형의 출력이 없는 경우 H4에 "No output of the same type as the input script" 추가
                else:
                    h4.append('Addresses of the same type as the input script are not unique')  # 입력 스크립트와 동일한 유형의 주소가 여러 개인 경우 H4에 "Addresses of the same type as the input script are not unique" 추가
            else:
                h4.append('There is only one type of output addresses')  # 출력 스크립트 유형이 하나인 경우 H4에 "There is only one type of output addresses" 추가
        else:
            h4.append('There are multiple types of input addresses')  # 입력 스크립트 유형이 여러 개인


        ''' H5'''
        ad_h5 = []  # H5에 해당하는 주소를 담을 리스트

        for i in range(len(output_receive)):
            if output_receive[i] % 1000 != 0:  # 수령 금액이 1000으로 나누어 떨어지지 않는 경우
                ad_h5.append(output_address[i])  # H5에 해당하는 주소를 ad_h5 리스트에 추가

        if len(ad_h5) == 0:
            h5.append('Receipts are all integers')  # 수령 금액이 모두 정수인 경우 H5에 "Receipts are all integers" 추가
        elif len(ad_h5) == 1:
            h5.append(ad_h5[0])  # H5에 해당하는 주소가 하나인 경우 그 주소를 추가
        else:
            h5.append('There are multiple non-integer recipient addresses')  # 수령 금액이 정수가 아닌 주소가 여러 개인 경우 H5에 "There are multiple non-integer recipient addresses" 추가
        '''위 코드는 수령 금액이 1000으로 나누어 떨어지지 않는 경우를 확인하고 해당 주소를 H5에 추가하는 부분'''

        '''H6'''
        if input_count>1:
            ad_h6 = []
            smallest = min(intput_sending)
            for i in range(len(output_receive)):
                if output_receive[i] < smallest:
                    ad_h6.append(output_address[i])
            if len(ad_h6) == 0:
                h6.append('Output address receipts are not smaller than all input')
            elif len(ad_h6) == 1:
                h6.append(ad_h6[0])
            else:
                h6.append('There are multiple address collections less than all inputs')
        else:
            h6.append('Single Input Transaction')
        '''위 코드는 input이 1보다 큰 경우를 처리하는 부분입니다. 가장 작은 intput_sending 값을 찾고, 그보다 작은 output_receive를 가진 주소를 H6에 추가합니다. 모든 input보다 작은 output이 없는 경우와 여러 개인 경우에 대한 조건을 처리하고 결과를 H6에 저장합니다. input이 하나인 경우에는 "Single Input Transaction"을 H6에 추가합니다.'''
    
        '''H7'''
        ad_candidate = []  # 조건을 검사할 주소를 담을 리스트

        for ad in output_address:
            if ad_info[ad_info['address_hash'] == ad]['output_count'].values[0] == 1:
                ad_candidate.append(ad)  # output_count가 1인 주소를 ad_candidate 리스트에 추가

        if self_change_tx != [] and self_change_tx[0] == 'self-change':
            condition1.append('self-change')
            condition2.append('self-change')
            condition3.append('self-change')
        elif len(ad_candidate) == 0:
            condition1.append('There are no new addresses in the output that have not been reused')
            condition2.append('There are no new addresses in the output that have not been reused')
            condition3.append('There are no new addresses in the output that have not been reused')
        else:
            '''condition1'''
            if len(set(input_script)) == 1:
                if len(set(output_script)) > 1:
                    ad_equal = []  # input script와 같은 타입의 주소를 담을 리스트
                    input_script_type = input_script[0]

                    for ad in ad_candidate:
                        if ad_script_dic[ad] == input_script_type:
                            ad_equal.append(ad)  # input script와 같은 타입의 주소를 ad_equal 리스트에 추가

                    if len(ad_equal) == 1:
                        condition1.append(ad_equal[0])  # ad_equal 리스트에 하나의 주소만 있는 경우 그 주소를 condition1에 추가
                    elif len(ad_equal) == 0:
                        condition1.append('No output of the same type as the input script')  # input script와 같은 타입의 output이 없는 경우 "No output of the same type as the input script"을 condition1에 추가
                    else:
                        condition1.append('Addresses of the same type as the input script are not unique')  # input script와 같은 타입의 output이 여러 개인 경우 "Addresses of the same type as the input script are not unique"을 condition1에 추가
                else:
                    condition1.append('There is only one type of output addresses')  # output script의 타입이 하나인 경우 "There is only one type of output addresses"을 condition1에 추가
            else:
                condition1.append('There are multiple types of input addresses')  # input script의 타입이 여러 개인 경우 "There are multiple types of input addresses"을 condition1에 추가


            '''condition2  condition3 '''
            ad_non_integer = []  # 정수가 아닌 주소를 담을 리스트
            ad_small = []  # smallest보다 작은 주소를 담을 리스트
            smallest = min(intput_sending)  # intput_sending 중 가장 작은 값

            for ad in ad_candidate:
                if (output_dict[ad] % 1000 != 0) and (output_dict_usd[ad] % 100 != 0):
                    ad_non_integer.append(ad)  # 정수가 아닌 경우 ad_non_integer 리스트에 추가
                if output_dict[ad] < smallest:
                    ad_small.append(ad)  # smallest보다 작은 경우 ad_small 리스트에 추가

            '''condition2'''
            if len(ad_non_integer) == 1:
                address_others = list(set(output_address) - set(ad_non_integer))  # ad_non_integer에 속하지 않는 다른 주소들의 리스트
                integer_num = 0

                for ad in address_others:
                    if (output_dict[ad] % 1000 == 0) or (output_dict_usd[ad] % 100 == 0):
                        integer_num += 1  # 정수인 주소의 개수 세기

                if integer_num == len(address_others):
                    condition2.append(ad_non_integer[0])  # 다른 주소들이 모두 정수인 경우 ad_non_integer의 첫 번째 주소를 condition2에 추가
                else:
                    condition2.append('Other addresses collections are not all integers')  # 다른 주소들 중 정수인 주소가 아닌 경우 "Other addresses collections are not all integers"를 condition2에 추가
            elif len(ad_non_integer) == 0:
                condition2.append('No output address for non-integer collections')  # 정수가 아닌 주소가 없는 경우 "No output address for non-integer collections"를 condition2에 추가
            else:
                condition2.append('Output addresses with multiple non-integer collections')  # 정수가 아닌 주소가 여러 개인 경우 "Output addresses with multiple non-integer collections"을 condition2에 추가


            '''condition3'''
        if len(ad_small) == 1:
            condition3.append(ad_small[0])  # ad_small에 속하는 주소가 하나인 경우 condition3에 추가
        elif len(ad_small) == 0:
            condition3.append('No output address collection less than all inputs')  # ad_small이 없는 경우 "No output address collection less than all inputs"를 condition3에 추가
        else:
            condition3.append('Output addresses smaller than all inputs are not unique')  # ad_small이 여러 개인 경우 "Output addresses smaller than all inputs are not unique"을 condition3에 추가

        if condition1[-1] == condition2[-1] == condition3[-1]:
            h7.append(condition1[-1])  # condition1, condition2, condition3이 모두 동일한 경우 h7에 추가
        else:
            ad_set = set()
            if condition1[-1] in output_address:
                ad_set = ad_set | {condition1[-1]}  # condition1의 주소를 ad_set에 추가
            if condition2[-1] in output_address:
                ad_set = ad_set | {condition2[-1]}  # condition2의 주소를 ad_set에 추가
            if condition3[-1] in output_address:
                ad_set = ad_set | {condition3[-1]}  # condition3의 주소를 ad_set에 추가

            if len(ad_set) == 1:
                h7.append(list(ad_set)[0])  # ad_set에 속하는 주소가 하나인 경우 h7에 추가
            elif len(ad_set) == 0:
                h7.append('New addresses that are not reused do not satisfy conditions 1-3')  # ad_set이 없는 경우 "New addresses that are not reused do not satisfy conditions 1-3"을 h7에 추가
            else:
                h7.append('Conditions 1-3 identify different results')  # ad_set이 여러 개인 경우 "Conditions 1-3 identify different results"을 h7에 추가

    else:
        h2.append('Single-output')  # h2에 'Single-output' 추가
        h3.append('Single-output')  # h3에 'Single-output' 추가
        h4.append('Single-output')  # h4에 'Single-output' 추가
        h5.append('Single-output')  # h5에 'Single-output' 추가
        h6.append('Single-output')  # h6에 'Single-output' 추가
        condition1.append('Single-output')  # condition1에 'Single-output' 추가
        condition2.append('Single-output')  # condition2에 'Single-output' 추가
        condition3.append('Single-output')  # condition3에 'Single-output' 추가
        h7.append('Single-output')  # h7에 'Single-output' 추가

    k += 1
    if k % 100 == 0:
        print('The time taken to execute {} times is: {}s'.format(k, time.time() - start_time))  # 매 100번째 반복마다 실행 시간 출력

    results = pd.DataFrame({'tx_hash': tx_list, 'tx_type': tx_type, 'h2': h2, 'h3': h3, 'h4': h4, 'h5': h5, 'h6': h6,
                            'condition1': condition1, 'condition2': condition2,
                            'condition3': condition3, 'h7': h7})  # 결과를 DataFrame으로 생성

    results = pd.merge(results, tx[['tx_hash', 'block_id']], on='tx_hash', how='left')  # 결과에 블록 ID 추가

    return results  # 결과 반환

    change_ad_result = change_address_identify(tx, input_data, output_data, ad_info, tx_list, ad_script_dic)  # change_address_identify 함수 호출하여 결과 저장


'''Trend of transactions, number of addresses with blocks'''

def tx_ad_count(tx, input_data, output_data):
    block_list = list(set(tx['block_id'].to_list()))  # 트랜잭션이 포함된 블록 ID 목록을 가져옴
    block_list.sort()  # 블록 ID를 오름차순으로 정렬
    tx_ad_num = pd.DataFrame(columns=['tx_num', 'ad_num_input', 'ad_num_output'])  # 결과를 저장할 DataFrame 생성
    for i in block_list:
        tx_block_i = tx[tx['block_id'] <= i]  # 현재 블록 ID까지의 트랜잭션 필터링
        input_data_block_i = input_data[input_data['block_id'] <= i]  # 현재 블록 ID까지의 입력 데이터 필터링
        output_data_block_i = output_data[output_data['block_id'] <= i]  # 현재 블록 ID까지의 출력 데이터 필터링
        tx_num = len(set(tx_block_i['tx_hash'].tolist()))  # 현재 블록까지의 고유한 트랜잭션 수 계산
        ad_num_input = len(set(input_data_block_i['address_hash'].tolist()))  # 현재 블록까지의 고유한 입력 주소 수 계산
        ad_num_output = len(set(output_data_block_i['address_hash'].tolist()))  # 현재 블록까지의 고유한 출력 주소 수 계산
        tx_ad_num.loc[i] = [tx_num, ad_num_input, ad_num_output]  # 결과 DataFrame에 행 추가

    return tx_ad_num

tx_ad_num = tx_ad_count(tx, input_data, output_data)  # tx_ad_count 함수 호출하여 결과 저장

print('Trend of transactions, number of addresses with blocks')
print(tx_ad_num)  # 결과 출력
print('------')
'''위 코드는 블록별로 트랜잭션 수와 입력/출력 주소 수의 추이를 보여주는 함수 tx_ad_count를 정의하고 호출합니다. 각 블록 ID별로 해당 블록까지의 트랜잭션 수와 입력/출력 주소 수를 계산하고, 이를 tx_ad_num DataFrame에 저장합니다. 그리고 결과를 출력합니다.'''

'''Transaction Type Distribution'''

def tx_type_distribution(dataset):
    tx_type_distri = pd.DataFrame(columns=['Single-output', 'Single-input 2-output', 'Multi-input 2-output', 'Multiple-input multiple-output', 'Single-input multiple-output'])
    block_list = list(set(dataset['block_id'].to_list()))  # 데이터셋에 포함된 블록 ID 목록을 가져옴
    block_list.sort()  # 블록 ID를 오름차순으로 정렬
    for i in block_list:
        block_tx_type = dataset[dataset['block_id'] <= i]  # 현재 블록 ID까지의 데이터셋 필터링
        tx_type_count = block_tx_type['tx_type'].value_counts()  # 현재 블록까지의 트랜잭션 유형별 개수 계산
        tx_type_count = np.array([tx_type_count['Single-output'], tx_type_count['Single-input 2-output'], tx_type_count['Multi-input 2-output'], tx_type_count['Multiple-input multiple-output'], tx_type_count['Single-input multiple-output']])
        sample = tx_type_count / np.sum(tx_type_count)  # 각 트랜잭션 유형의 비율 계산
        tx_type_distri.loc[i] = sample  # 결과 DataFrame에 행 추가
    return tx_type_distri

tx_type_distribution = tx_type_distribution(change_ad_result)  # tx_type_distribution 함수 호출하여 결과 저장

print('Transaction Type Distribution:')
print(tx_type_distribution)  # 결과 출력
print('------')
'''위 코드는 데이터셋 내 트랜잭션 유형의 분포를 보여주는 함수 tx_type_distribution을 정의하고 호출합니다. 각 블록 ID별로 해당 블록까지의 데이터셋을 필터링하고, 트랜잭션 유형별 개수를 계산하여 비율로 변환합니다. '''

'''Counting the number of change addresses identified by H2-H7'''

def non_address(change_ads, addresses_set):
    non_ad = []
    for ad in change_ads:
        if ad not in addresses_set:
            non_ad.append(ad)
    return set(non_ad)
'''non_address 함수는 change_ads 리스트에서 addresses_set에 속하지 않는 주소들을 추출하여 집합(set)으로 반환합니다.'''

def identity_num(data, h, elements_removed):
    change_ads = set(data[h].tolist())  # data[h] 열의 고유한 값들을 set으로 변환하여 저장
    change_ads = change_ads - elements_removed  # elements_removed에서 제외된 값들을 제외
    return change_ads
'''identity_num 함수는 data 데이터프레임의 h 열에 있는 고유한 값들을 집합(set)으로 반환합니다. 이 때, elements_removed에 포함된 값들은 제외됩니다.'''

def change_ad_count(output_data, data, block_list):
    # 출력 주소 집합 설정
    output_ad_set = set(output_data['address_hash'].tolist())
    
    # 각 열의 고유한 값들을 리스트로 추출
    c1_ad_list = list(set(data['condition1'].tolist()))
    c2_ad_list = list(set(data['condition2'].tolist()))
    c3_ad_list = list(set(data['condition3'].tolist()))
    h7_ad_list = list(set(data['h7'].tolist()))
    h2_ad_list = list(set(data['h2'].tolist()))
    h3_ad_list = list(set(data['h3'].tolist()))
    h4_ad_list = list(set(data['h4'].tolist()))
    h5_ad_list = list(set(data['h5'].tolist()))
    h6_ad_list = list(set(data['h6'].tolist()))
    
    # 각 조건에 해당하지 않는 주소들 추출
    c1_non_ad = non_address(c1_ad_list, output_ad_set)
    c2_non_ad = non_address(c2_ad_list, output_ad_set)
    c3_non_ad = non_address(c3_ad_list, output_ad_set)
    h7_non_ad = non_address(h7_ad_list, output_ad_set)
    h2_non_ad = non_address(h2_ad_list, output_ad_set)
    h3_non_ad = non_address(h3_ad_list, output_ad_set)
    h4_non_ad = non_address(h4_ad_list, output_ad_set)
    h5_non_ad = non_address(h5_ad_list, output_ad_set)
    h6_non_ad = non_address(h6_ad_list, output_ad_set)
    
    change_ad_num = pd.DataFrame(columns=['H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'c1', 'c2', 'c3'])
    
    for i in block_list:
        block_tx_type = data[data['block_id'] <= i]  # 블록 범위 내의 데이터 추출
        # 각 조건에 해당하는 주소들의 수 계산
        c1 = len(identity_num(block_tx_type, 'condition1', c1_non_ad))
        c2 = len(identity_num(block_tx_type, 'condition2', c2_non_ad))
        c3 = len(identity_num(block_tx_type, 'condition3', c3_non_ad))
        h7 = len(identity_num(block_tx_type, 'h7', h7_non_ad))
        h2 = len(identity_num(block_tx_type, 'h2', h2_non_ad))
        h3 = len(identity_num(block_tx_type, 'h3', h3_non_ad))
        h4 = len(identity_num(block_tx_type, 'h4', h4_non_ad))
        h5 = len(identity_num(block_tx_type, 'h5', h5_non_ad))
        h6 = len(identity_num(block_tx_type, 'h6', h6_non_ad))
        
        sample = [h2, h3, h4, h5, h6, h7, c1, c2, c3]
        change_ad_num.loc[i] = sample  # 결과 데이터프레임에 추가
        
    return change_ad_num


def change_ad_num(change_ad_result):
    block_list = list(set(change_ad_result['block_id'].to_list()))
    block_list.sort()
    
    # 각 트랜잭션 유형에 해당하는 데이터 추출
    data1 = change_ad_result[change_ad_result['tx_type'] == 'Single-input 2-output']
    data2 = change_ad_result[change_ad_result['tx_type'] == 'Multi-input 2-output']
    data3 = change_ad_result[change_ad_result['tx_type'] == 'Multiple-input multiple-output']
    data4 = change_ad_result[change_ad_result['tx_type'] == 'Single-input multiple-output']

    # 모든 트랜잭션 유형에 대한 변경 주소 수 계산
    change_ad_num_all = change_ad_count(output_data, change_ad_result, block_list)
    
    # 각 트랜잭션 유형에 대한 변경 주소 수 계산
    change_ad_num_1 = change_ad_count(output_data, data1, block_list)
    change_ad_num_2 = change_ad_count(output_data, data2, block_list)
    change_ad_num_3 = change_ad_count(output_data, data3, block_list)
    change_ad_num_4 = change_ad_count(output_data, data4, block_list)

    return change_ad_num_all, change_ad_num_1, change_ad_num_2, change_ad_num_3, change_ad_num_4
'''change_ad_num 함수는 주어진 change_ad_result 데이터프레임에 대해 모든 트랜잭션 유형 및 각각의 트랜잭션 유형에 대한 변경 주소 수를 계산합니다.'''
change_ad_num_all, change_ad_num_1, change_ad_num_2, change_ad_num_3, change_ad_num_4 = change_ad_num(change_ad_result)

print('Change address recognition results')
print(change_ad_num_all)
print('------')



'''Regression relationship between change address and number of transactions'''
lm_h7=ols('H7~block_num',data=change_ad_num_all).fit()
lm_h2=ols('H2~block_num',data=change_ad_num_all).fit()
lm_h3=ols('H3~block_num',data=change_ad_num_all).fit()
lm_h4=ols('H4~block_num',data=change_ad_num_all).fit()
lm_h5=ols('H5~block_num',data=change_ad_num_all).fit()
lm_h6=ols('H6~block_num',data=change_ad_num_all).fit()

print('Regression relationship between change address and number of transactions')
print(lm_h2.summary())
print(lm_h3.summary())
print(lm_h4.summary())
print(lm_h5.summary())
print(lm_h6.summary())
print(lm_h7.summary())
print('------')
'''각각 lm_h2, lm_h3, lm_h4, lm_h5, lm_h6, lm_h7은 변경 주소(H2, H3, H4, H5, H6, H7)와 블록 수(block_num) 간의 선형 회귀 모델을 적합한 결과입니다.'''

'''Recognition rate of different methods'''

def h_identity_rate(data,h,tx_type_freq,elements_removed):
    change_ads=set(data[h].tolist())
    change_ads=list(change_ads-elements_removed)
    df1 =data[data[h].isin(change_ads)]
    tx_type_count = df1['tx_type'].value_counts()
    sample=[]
    index_type=list(tx_type_count.index)
    if 'Single-input 2-output' in index_type:
        sample.append(tx_type_count['Single-input 2-output'])
    else:
        sample.append(0)
    if 'Multi-input 2-output' in index_type:
        sample.append(tx_type_count['Multi-input 2-output'])
    else:
        sample.append(0)
    if 'Multiple-input multiple-output' in index_type:
        sample.append(tx_type_count['Multiple-input multiple-output'])
    else:
        sample.append(0)
    if 'Single-input multiple-output' in index_type:
        sample.append(tx_type_count['Single-input multiple-output'])
    else:
        sample.append(0)
    tx_type_count = np.array(sample)
    tx_type_count = tx_type_count / tx_type_freq
    return np.around(tx_type_count,decimals=3)

'''위 코드는 주어진 데이터에서 주어진 조건(h)에 해당하는 변경 주소의 식별률(Recognition rate)을 계산하는 함수입니다.'''

output_ad_set=set(output_data['address_hash'].tolist())
c1_ad_list=list(set(change_ad_result['condition1'].tolist()))
c2_ad_list=list(set(change_ad_result['condition2'].tolist()))
c3_ad_list=list(set(change_ad_result['condition2'].tolist()))
h7_ad_list=list(set(change_ad_result['h7'].tolist()))
h2_ad_list=list(set(change_ad_result['h2'].tolist()))
h3_ad_list=list(set(change_ad_result['h3'].tolist()))
h4_ad_list=list(set(change_ad_result['h4'].tolist()))
h5_ad_list=list(set(change_ad_result['h5'].tolist()))
h6_ad_list=list(set(change_ad_result['h6'].tolist()))

c1_non_ad=non_address(c1_ad_list,output_ad_set)
c2_non_ad=non_address(c2_ad_list,output_ad_set)
c3_non_ad=non_address(c3_ad_list,output_ad_set)
h7_non_ad=non_address(h7_ad_list,output_ad_set)
h2_non_ad=non_address(h2_ad_list,output_ad_set)
h3_non_ad=non_address(h3_ad_list,output_ad_set)
h4_non_ad=non_address(h4_ad_list,output_ad_set)
h5_non_ad=non_address(h5_ad_list,output_ad_set)
h6_non_ad=non_address(h6_ad_list,output_ad_set)

tx_type_freq=change_ad_result['tx_type'].value_counts()
tx_type_freq=np.array([tx_type_freq['Single-input 2-output'],tx_type_freq['Multi-input 2-output'],tx_type_freq['Multiple-input multiple-output'],tx_type_freq['Single-input multiple-output']])
h7_tx=h_identity_rate(change_ad_result,'h7',tx_type_freq,h7_non_ad)
h2_tx=h_identity_rate(change_ad_result,'h2',tx_type_freq,h2_non_ad)
h3_tx=h_identity_rate(change_ad_result,'h3',tx_type_freq,h3_non_ad)
h4_tx=h_identity_rate(change_ad_result,'h4',tx_type_freq,h4_non_ad)
h5_tx=h_identity_rate(change_ad_result,'h5',tx_type_freq,h5_non_ad)
h6_tx=h_identity_rate(change_ad_result,'h6',tx_type_freq,h6_non_ad)
h_tx_type=pd.DataFrame([h7_tx,h2_tx,h3_tx,h4_tx,h5_tx,h6_tx],columns=['Single-input 2-output', 'Multi-input 2-output', 'Multiple-input multiple-output','Single-input multiple-output'],index=['H7','H2','H3','H4','H5','H6'])

print('Recognition rate of different methods')
print(h_tx_type)
print('------')


'''Coverage of H2-H6 by H7'''

def covered(output_data,change_ad_result):

    output_addresses = set(output_data['address_hash'].tolist())
    h7_ad_list = change_ad_result['h7'].tolist()
    h2_ad_list = change_ad_result['h2'].tolist()
    h3_ad_list = change_ad_result['h3'].tolist()
    h4_ad_list = change_ad_result['h4'].tolist()
    h5_ad_list = change_ad_result['h5'].tolist()
    h6_ad_list = change_ad_result['h6'].tolist()

    h7_vs_h2_overlap = []
    h7_vs_h2_not_overlap = []
    h7_vs_h3_overlap = []
    h7_vs_h3_not_overlap = []
    h7_vs_h4_overlap = []
    h7_vs_h4_not_overlap = []
    h7_vs_h5_overlap = []
    h7_vs_h5_not_overlap = []
    h7_vs_h6_overlap = []
    h7_vs_h6_not_overlap = []
    h7_change_ad=identity_num(change_ad_result,'h7',h7_non_ad)
    for i in range(len(h7_ad_list)):
        h7_ad = h7_ad_list[i]
        h2_ad = h2_ad_list[i]
        h3_ad = h3_ad_list[i]
        h4_ad = h4_ad_list[i]
        h5_ad = h5_ad_list[i]
        h6_ad = h6_ad_list[i]
        if h2_ad in output_addresses:
            if h2_ad == h7_ad:
                h7_vs_h2_overlap.append(h7_ad)
            elif h2_ad not in h7_change_ad:
                if h7_ad not in h7_change_ad:
                    h7_vs_h2_not_overlap.append(h7_ad)
                else:
                    h7_vs_h2_not_overlap.append('Different from the change address identified by H7')
        if h3_ad in output_addresses:
            if h3_ad == h7_ad:
                h7_vs_h3_overlap.append(h7_ad)
            elif h3_ad not in h7_change_ad:
                if h7_ad not in h7_change_ad:
                    h7_vs_h3_not_overlap.append(h7_ad)
                else:
                    h7_vs_h3_not_overlap.append('Different from the change address identified by H7')
        if h4_ad in output_addresses:
            if h4_ad == h7_ad:
                h7_vs_h4_overlap.append(h7_ad)
            elif h4_ad not in h7_change_ad:
                if h7_ad not in h7_change_ad:
                    h7_vs_h4_not_overlap.append(h7_ad)
                else:
                    h7_vs_h4_not_overlap.append('Different from the change address identified by H7')
        if h5_ad in output_addresses:
            if h5_ad == h7_ad:
                h7_vs_h5_overlap.append(h7_ad)
            elif h5_ad not in h7_change_ad:
                if h7_ad not in h7_change_ad:
                    h7_vs_h5_not_overlap.append(h7_ad)
                else:
                    h7_vs_h5_not_overlap.append('Different from the change address identified by H7')
        if h6_ad in output_addresses:
            if h6_ad == h7_ad:
                h7_vs_h6_overlap.append(h7_ad)
            elif h6_ad not in h7_change_ad:
                if h7_ad not in h7_change_ad:
                    h7_vs_h6_not_overlap.append(h7_ad)
                else:
                    h7_vs_h6_not_overlap.append('Different from the change address identified by H7')
    return h7_vs_h2_overlap,h7_vs_h2_not_overlap,h7_vs_h3_overlap,h7_vs_h3_not_overlap,h7_vs_h4_overlap,h7_vs_h4_not_overlap,h7_vs_h5_overlap,h7_vs_h5_not_overlap,h7_vs_h6_overlap,h7_vs_h6_not_overlap

def frequency(h_not_covered):
    index_type=h_not_covered.index
    sample_freq=[]
    if 'self-change' in index_type:
        sample_freq.append(h_not_covered['self-change'])
    else:
        sample_freq.append(0)
    if 'There are no new addresses in the output that have not been reused' in index_type:
        sample_freq.append(h_not_covered['There are no new addresses in the output that have not been reused'])
    else:
        sample_freq.append(0)
    if 'Different from the change address identified by H7' in index_type:
        sample_freq.append(h_not_covered['Different from the change address identified by H7'])
    else:
        sample_freq.append(0)
    if 'New addresses that are not reused do not satisfy conditions 1-3' in index_type:
        sample_freq.append(h_not_covered['New addresses that are not reused do not satisfy conditions 1-3'])
    else:
        sample_freq.append(0)
    if 'Conditions 1-3 identify different results' in index_type:
        sample_freq.append(h_not_covered['Conditions 1-3 identify different results'])
    else:
        sample_freq.append(0)
    return np.array(sample_freq)

h7_vs_h2_overlap,h7_vs_h2_not_overlap,h7_vs_h3_overlap,h7_vs_h3_not_overlap,h7_vs_h4_overlap,h7_vs_h4_not_overlap,h7_vs_h5_overlap,h7_vs_h5_not_overlap,h7_vs_h6_overlap,h7_vs_h6_not_overlap=covered(output_data,change_ad_result)

coverage=np.array([len(h7_vs_h2_overlap),len(h7_vs_h3_overlap),len(h7_vs_h4_overlap),len(h7_vs_h5_overlap),len(h7_vs_h6_overlap)])/change_ad_num_all[['H2','H3','H4','H5','H6']].loc[738789].to_numpy()

h2_not_covered=pd.Series(h7_vs_h2_not_overlap).value_counts()
h3_not_covered=pd.Series(h7_vs_h3_not_overlap).value_counts()
h4_not_covered=pd.Series(h7_vs_h4_not_overlap).value_counts()
h5_not_covered=pd.Series(h7_vs_h5_not_overlap).value_counts()
h6_not_covered=pd.Series(h7_vs_h6_not_overlap).value_counts()

df_not_covered=pd.DataFrame(columns=['self-change','There are no new addresses in the output that have not been reused','Different from the change address identified by H7','New addresses that are not reused do not satisfy conditions 1-3','Conditions 1-3 identify different results'])
df_not_covered.loc['h2_not_covered']=frequency(h2_not_covered)/np.sum(frequency(h2_not_covered))
df_not_covered.loc['h3_not_covered']=frequency(h3_not_covered)/np.sum(frequency(h3_not_covered))
df_not_covered.loc['h4_not_covered']=frequency(h4_not_covered)/np.sum(frequency(h4_not_covered))
df_not_covered.loc['h5_not_covered']=frequency(h5_not_covered)/np.sum(frequency(h5_not_covered))
df_not_covered.loc['h6_not_covered']=frequency(h6_not_covered)/np.sum(frequency(h6_not_covered))

print('Coverage of H2-H6 by H7')
print(coverage)
print(df_not_covered)
print('------')

'''Construct a transaction-input address set dictionary based on transaction hashes and input addresses'''
def tx_adset_dict(input_data):
    tx_adset_dict = {}
    tx_list=input_data['tx_hash'].tolist()
    for t in tx_list:
        tx_input = input_data[input_data['tx_hash'] == t]
        input_ad_set = set(tx_input['address_hash'].tolist())
        tx_adset_dict[t] = input_ad_set
    return tx_adset_dict

def tx_encoding(tx_adset_dict):
    t_list=list(tx_adset_dict.keys())
    txin_user_id = {t_list[i]: i for i in range(len(t_list))}
    l1 = len(t_list)

    while l1>0:
        tx_hash_l1=t_list[l1-1]
        l2=l1-1
        while l2>0:
            tx_hash_l2 =t_list[l2-1]
            if len(tx_adset_dict[tx_hash_l1] & tx_adset_dict[tx_hash_l2])!=0:
                txin_user_id[tx_hash_l2]=txin_user_id[tx_hash_l1]
                tx_adset_dict[tx_hash_l1]=tx_adset_dict[tx_hash_l1]|tx_adset_dict[tx_hash_l2]
                t_list.remove(tx_hash_l2)
                l1-=1
            l2-=1
        l1-=1

    tx_list2 = list(txin_user_id.keys())
    user_id = [txin_user_id[t] for t in tx_list2]
    input_user_id = pd.DataFrame({'tx_hash': tx_list2, 'user_id': user_id})

    return input_user_id

'''Address Clustering：H1,H1+Hi,i=2,3,4,5,6,7'''

def multi_input_address_clustering(input_data,output_data,txin_user_id):
    ad_user_id = {}
    input_addresses = list(set(input_data['address_hash'].tolist()))
    output_addresses = list(set(output_data['address_hash'].tolist()))
    ad_list = list(set(input_addresses + output_addresses))

    input_data = pd.merge(input_data, txin_user_id, on='tx_hash', how='left')
    userid_list = input_data['user_id'].tolist()
    input_addresses = input_data['address_hash'].tolist()
    for i in range(len(input_addresses)):
        ad_user_id[input_addresses[i]] = userid_list[i]

    ad_list2 = set(ad_list) - set(list(ad_user_id.keys()))
    id = 0
    for ad in ad_list2:
        ad_user_id[ad] = txin_user_id.shape[0] + id
        id += 1
    input_data.drop(['user_id'], axis=1, inplace=True)
    return ad_user_id

def change_ad_h(input_data,output_data,tx_change_ad_dict,txin_user_id):
    ad_user_id={}
    input_addresses=list(set(input_data['address_hash'].tolist()))
    output_addresses=list(set(output_data['address_hash'].tolist()))
    ad_list=list(set(input_addresses+output_addresses))

    t_list = txin_user_id['tx_hash'].tolist()
    user_id = txin_user_id['user_id'].tolist()
    txin_user_id = {t_list[i]: user_id[i] for i in range(len(t_list))}

    for key in tx_change_ad_dict.keys():
        address = tx_change_ad_dict[key]
        if address in input_addresses:
            t_list1 = list(set(input_data[input_data['address_hash'] == address]['tx_hash'].tolist()))
            for t in t_list1:
                txin_user_id[t] = txin_user_id[key]
        else:
            ad_user_id[address] = txin_user_id[key]

    txin_user_id=pd.DataFrame({'tx_hash':t_list,'user_id':user_id})
    input_data = pd.merge(input_data, txin_user_id, on='tx_hash', how='left')
    userid_list = input_data['user_id'].tolist()
    input_addresses = input_data['address_hash'].tolist()
    for i in range(len(input_addresses)):
        ad_user_id[input_addresses[i]] = userid_list[i]

    ad_list2=set(ad_list)-set(list(ad_user_id.keys()))
    id=0
    for ad in ad_list2:
        ad_user_id[ad]=len(t_list)+id
        id+=1
    input_data.drop(['user_id'],axis=1,inplace=True)
    return ad_user_id

height_k=[738699,738709,738719,738729,738739,738749,738759,738769,738779,738789]

clustering_result=pd.DataFrame(columns=['H1','H2','H3','H4','H5','H6','H7'])

for height in height_k:

    data_height=change_ad_result[change_ad_result['block_id']<=height]
    input_data_height = input_data[input_data['block_id'] <= height]
    output_data_height = output_data[output_data['block_id'] <= height]
    tx_adset_dict_height=tx_adset_dict(input_data_height)
    tx_coding_result_height=tx_encoding(tx_adset_dict_height)

    tx_list = data_height['tx_hash'].tolist()
    output_addresses = set(output_data_height['address_hash'].tolist())
    h7_change_ad = data_height['h7'].tolist()
    h2_change_ad = data_height['h2'].tolist()
    h3_change_ad = data_height['h3'].tolist()
    h4_change_ad = data_height['h4'].tolist()
    h5_change_ad = data_height['h5'].tolist()
    h6_change_ad = data_height['h6'].tolist()

    tx_change_ad_h7_dict = {tx_list[i]: h7_change_ad[i] for i in range(len(tx_list)) if
                              h7_change_ad[i] in output_addresses}
    tx_change_ad_h2_dict = {tx_list[i]: h2_change_ad[i] for i in range(len(tx_list)) if
                            h2_change_ad[i] in output_addresses}
    tx_change_ad_h3_dict = {tx_list[i]: h3_change_ad[i] for i in range(len(tx_list)) if
                            h3_change_ad[i] in output_addresses}
    tx_change_ad_h4_dict = {tx_list[i]: h4_change_ad[i] for i in range(len(tx_list)) if
                            h4_change_ad[i] in output_addresses}
    tx_change_ad_h5_dict = {tx_list[i]: h5_change_ad [i] for i in range(len(tx_list)) if
                            h5_change_ad [i] in output_addresses}
    tx_change_ad_h6_dict = {tx_list[i]: h6_change_ad[i] for i in range(len(tx_list)) if
                            h6_change_ad[i] in output_addresses}

    multi_input_result=multi_input_address_clustering(input_data_height,output_data_height,tx_coding_result_height)
    h7_clustering_result=change_ad_h(input_data_height,output_data_height,tx_change_ad_h7_dict,tx_coding_result_height)
    h2_clustering_result=change_ad_h(input_data_height,output_data_height,tx_change_ad_h2_dict,tx_coding_result_height)
    h3_clustering_result=change_ad_h(input_data_height,output_data_height,tx_change_ad_h3_dict,tx_coding_result_height)
    h4_clustering_result=change_ad_h(input_data_height,output_data_height,tx_change_ad_h4_dict,tx_coding_result_height)
    h5_clustering_result=change_ad_h(input_data_height,output_data_height,tx_change_ad_h5_dict,tx_coding_result_height)
    h6_clustering_result=change_ad_h(input_data_height,output_data_height,tx_change_ad_h6_dict,tx_coding_result_height)

    clustering_result.loc[height]=[len(set(multi_input_result.values())),len(set(h2_clustering_result.values())),len(set(h3_clustering_result.values())),len(set(h4_clustering_result.values())),len(set(h5_clustering_result.values())),len(set(h6_clustering_result.values())),len(set(h7_clustering_result.values()))]

print('Result of address clustering')
print(clustering_result)
print('------')

'''Address reduction rate'''
def ad_reduce_rate(clustering_result,input_data,output_data):
    r=pd.DataFrame(columns=['H1','H2','H3','H4','H5','H6','H7'])

    for height in clustering_result.index:
        ad_num=len(set(input_data[input_data['block_id']<=height]['address_hash'].tolist()))+len(set(output_data[output_data['block_id']<=height]['address_hash'].tolist()))
        h1_cluster_num=clustering_result.loc[height]['H1']
        h2_cluster_num = clustering_result.loc[height]['H2']
        h3_cluster_num = clustering_result.loc[height]['H3']
        h4_cluster_num = clustering_result.loc[height]['H4']
        h5_cluster_num = clustering_result.loc[height]['H5']
        h6_cluster_num = clustering_result.loc[height]['H6']
        h7_cluster_num = clustering_result.loc[height]['H7']

        r.loc[height]=(ad_num-np.array([h1_cluster_num,h2_cluster_num,h3_cluster_num,h4_cluster_num,h5_cluster_num,h6_cluster_num,h7_cluster_num]))/ad_num
    return r

r=ad_reduce_rate(clustering_result,input_data,output_data)

print('Address reduction rate')
print(r)
print('------')


