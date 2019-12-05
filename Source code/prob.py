from argparse import ArgumentParser
import os
import sys

"""
Disease Name and Abbreviation:

    AD = Alzheimer’s disease
    DLB = Lewy body type of dementia
    VaD = Vascular dementia
    epiMem = Episodic memory dysfunction
    fluctCog = Fluctuating cognition
    fn = Focal neurological signs
    prog = Progressive course
    radVasc = Radiology exam shows vascular signs
    slow = Slow, gradual onset
    extraPyr = Extrapyramidal symptoms
    visHall = Visual hallucinations

Labesl : 
    confirmed > probable >= plausible > possible > supported > open

"""

def read_file(filepath):
    """
    input : str -> "Rule.txt"
    output : list[str]
    """

    def change_or_sign(line):
        for idx,c in enumerate(line):
                if idx>0 and c=='v' and line[idx-1]==" " and line[idx+1]==" " :
                    line = line[:idx] + "~" + line[idx+1:] 
        return line

    data_line=[]
    with open(filepath, encoding='utf-8') as fp:
        for line in fp: 
            line = change_or_sign(line)            
            no_space_line = line.replace(" ","")
            data_line.append(no_space_line)

    return data_line

def split_and_sign(str_with_and_sign):
    """
    str_with_and_sign : str -> "fn ^ radVasc ^ not(AD ~ DLB)"

    return : 
        list[str] ->  [fn,radVasc,not(AD ~ DLB)]
    """
    split_symptom = []
    while True:
        split_idx = str_with_and_sign.find('^')

        if split_idx < 0: break
        else:
            symptom = str_with_and_sign[:split_idx]
            str_with_and_sign = str_with_and_sign[split_idx+1:]
            split_symptom.append(symptom)

    str_with_and_sign = str_with_and_sign.replace("\n","")
    split_symptom.append(str_with_and_sign[:])

    return split_symptom

def transform_str(rule):
    """
    rule : str -> "probable: VaD <- fn ^ radVasc ^ not(AD v DLB)"

    return :
        level_of_possibility : str -> probable
        Possible_Symptom     : str -> VaD
        Confirm_Symptom      : list[str] -> [fn,radVasc,not(AD ~ DLB)]
    """
    idx = rule.find("<-")
    left = rule[:idx]
    right = rule[idx+2:]

    left_idx = left.find(':')
    level_of_possibility = left[:left_idx]
    Possible_Symptom = left[left_idx+1:]

    Confirm_Symptom = split_and_sign(right)

    return level_of_possibility,Possible_Symptom,Confirm_Symptom

def delete_duplicate_element(_list):
    _set = set(element for element in _list)

    return [element for element in _set]

def compare_label_priorty(Label_A,Label_B,Labels):
    """
    if A is prior than B return True
    else return False
    """
    priority_1 = Labels.index(Label_A)
    priority_2 = Labels.index(Label_B)

    if priority_1 <= priority_2 : return True
    else : return False


def find_unique_answer_set(Potential_answer_sets,Labels):
    """
    Potential_answer_sets : list[dict] -> 
    [
        {'DLB': 'possible', 'VaD': 'probable'}
        {'DLB': 'probable', 'VaD': 'probable'}
    ]

    Labels : list -> [confirmed, probable, plausible, possible, supported, open]
    """
    unique_answer_set=Potential_answer_sets[0]

    for i in range(1,len(Potential_answer_sets)):
        second_set = Potential_answer_sets[i]

        for key in unique_answer_set:
            if compare_label_priorty(unique_answer_set[key],second_set[key],Labels)==False: 
                unique_answer_set = second_set
                break

    return unique_answer_set
        

def find_Potential_answer_set(Model,Labels):
    """
    Model : list[pair(str,str)] ->[('probable', 'VaD'),('probable', 'VaD^DLB'),..]
    Labels : list[str] -> ["confirmed","probable","plausible","possible","supported","open"]
    
    return : 
        list[dict] ->
            {'DLB': 'possible', 'VaD': 'probable', 'extraPyr': 'confirmed', 'fluctCog': 'confirmed', 'fn': 'confirmed', 'radVasc': 'confirmed'}
    """

    sort_Model = sorted(Model,key=lambda x:x[1])

    P_M = []
    target_idx,compare_idx=0,1
    while True:
        target = sort_Model[target_idx]

        if compare_idx >= len(Model) : 
            P_M.append(target)
            break
        else:
            compare_element = sort_Model[compare_idx]

        if target[1] == compare_element[1]:
            rt = compare_label_priorty(target[0],compare_element[0],Labels)
            
            if rt==False: target_idx = compare_idx
            compare_idx += 1
        else:
            P_M.append(target)

            target_idx = compare_idx
            compare_idx = compare_idx + 1
   
    for item in P_M:
        if "^" in item[1]:
            split_idx = item[1].find("^")

            P_M.remove(item)
            P_M.append((item[0],item[1][:split_idx]))
            P_M.append((item[0],item[1][split_idx+1:]))

    P_M = delete_duplicate_element(P_M)
    P_M = sorted(P_M,key=lambda x:x[1])

    Potential_answer_sets = []

    for i in range(len(P_M)-1):
        """
        p_answer_set = [{DLB:possible,VaD:probable},...]
        """
        p_answer_set={}
        p_answer_set[P_M[i][1]]=P_M[i][0]
        for j in range(len(P_M)):
            if P_M[i][1] == P_M[j][1]:  continue
            else : p_answer_set[P_M[j][1]]=P_M[j][0]

        if p_answer_set not in Potential_answer_sets:
            Potential_answer_sets.append(p_answer_set)


    return Potential_answer_sets

def get_potential_model(Patient_Comfirm_Symptoms,Labels,Complication,Symptoms): 
    """
    list types:
        labels -> ['confirmed','probable'...]
        Complication -> ['VaD','DLB','DLB^AD',...]
        Symptoms -> [['fn'], ['slow', 'prog', 'epiMem', 'not(VaD~DLB)'],...]
    """
    Model=[]
    for idx,cases in enumerate(Symptoms):
        Statify_case = True
        Not_flag = False
        for case in cases:
            if "not" in case: Not_flag=True

            if "~" in case:
                left_bracket_idx = case.find("(")
                right_bracket_idx = case.find(")")
                or_sign_idx = case.find("~")

                left_element = case[left_bracket_idx+1:or_sign_idx]
                right_element = case[or_sign_idx+1:right_bracket_idx]

                if Not_flag==True:
                    if (left_element in Patient_Comfirm_Symptoms) or (right_element in Patient_Comfirm_Symptoms):
                        Statify_case = False
                else:
                    if (left_element not in Patient_Comfirm_Symptoms) and (right_element not in Patient_Comfirm_Symptoms):
                        Statify_case = False

            else:
                if Not_flag==True: 
                    left_bracket_idx = case.find("(")
                    right_bracket_idx = case.find(")")

                    element = case[left_bracket_idx+1:right_bracket_idx]
                    if element in Patient_Comfirm_Symptoms:
                        Statify_case = False
                else:
                    if case not in Patient_Comfirm_Symptoms:
                        Statify_case = False

            if Statify_case==False : break             

        if Statify_case==True: Model.append((Labels[idx],Complication[idx]))

    return Model


if __name__ == "__main__":
    try:
        parser = ArgumentParser()
        parser.add_argument("Rule_text", help="rule text")
        parser.add_argument("Patient_text", help="patient text")
        args = parser.parse_args()


        patient_filepath = args.Patient_text #'Patient_1.txt'
        rule_filepath = args.Rule_text #'rule.txt'

        Labels = ["confirmed","probable","plausible","possible","supported","open"]

        patient = read_file(patient_filepath)
        rules = read_file(rule_filepath)
    except:
        print("\nUsage : ")
        print("python prob.py Rule.txt Patient_1.txt")
        sys.exit(0)


    confirm_data_set,confirm_disease=[],[]
    for confirm_data in patient:
        confirm_label,disease,_True = transform_str(confirm_data)
        if confirm_label=="confirmed": 
            confirm_disease.append(disease)
            confirm_data_set.append((confirm_label,disease))

    
    Case_Labels,Complication,Symptoms = [],[],[] #confirm, possible, plauible,....
    disease_relation = {}

    for p in rules:
        level_of_possibility,Possible_Symptom,Confirm_Symptom = transform_str(p)
        
        Case_Labels.append(level_of_possibility)
        Complication.append(Possible_Symptom)
        Symptoms.append(Confirm_Symptom)

    Model = get_potential_model(confirm_disease,Case_Labels,Complication,Symptoms)
    Model = Model + confirm_data_set
    Potential_answer_sets = find_Potential_answer_set(Model,Labels)
    
    unique_answer_set = find_unique_answer_set(Potential_answer_sets,Labels)

    print("Model : ")
    print(Model)
    
    print("\nPotential_answer_sets :")
    for sets in Potential_answer_sets: print(sets)

    print("\nUnique Anwser set : ")
    print(unique_answer_set)

