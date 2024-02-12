# python imports
import json


def get_skillsets_data(data):
    skillsets = []
    skillset_data = []
    temp_data = {}
    temp_data["init_qualify_ques_1"] = data.get("init_qualify_ques_1")
    temp_data["init_qualify_ques_weightage_1"] = data.get("init_qualify_ques_weightage_1")
    temp_data["init_qualify_ques_suggestion_1"] = json.loads(data.get("init_qualify_ques_suggestion_1"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_2"] = data.get("init_qualify_ques_2")
    temp_data["init_qualify_ques_weightage_2"] = data.get("init_qualify_ques_weightage_2")
    temp_data["init_qualify_ques_suggestion_2"] = json.loads(data.get("init_qualify_ques_suggestion_2"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_3"] = data.get("init_qualify_ques_3")
    temp_data["init_qualify_ques_weightage_3"] = data.get("init_qualify_ques_weightage_3")
    temp_data["init_qualify_ques_suggestion_3"] = json.loads(data.get("init_qualify_ques_suggestion_3"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_4"] = data.get("init_qualify_ques_4")
    temp_data["init_qualify_ques_weightage_4"] = data.get("init_qualify_ques_weightage_4")
    temp_data["init_qualify_ques_suggestion_4"] = json.loads(data.get("init_qualify_ques_suggestion_4"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_5"] = data.get("init_qualify_ques_5")
    temp_data["init_qualify_ques_weightage_5"] = data.get("init_qualify_ques_weightage_5")
    temp_data["init_qualify_ques_suggestion_5"] = json.loads(data.get("init_qualify_ques_suggestion_5"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_6"] = data.get("init_qualify_ques_6")
    temp_data["init_qualify_ques_weightage_6"] = data.get("init_qualify_ques_weightage_6")
    temp_data["init_qualify_ques_suggestion_6"] = json.loads(data.get("init_qualify_ques_suggestion_6"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_7"] = data.get("init_qualify_ques_7")
    temp_data["init_qualify_ques_weightage_7"] = data.get("init_qualify_ques_weightage_7")
    temp_data["init_qualify_ques_suggestion_7"] = json.loads(data.get("init_qualify_ques_suggestion_7"))
    skillset_data.append(temp_data)
    temp_data = {}
    temp_data["init_qualify_ques_8"] = data.get("init_qualify_ques_8")
    temp_data["init_qualify_ques_weightage_8"] = data.get("init_qualify_ques_weightage_8")
    temp_data["init_qualify_ques_suggestion_8"] = json.loads(data.get("init_qualify_ques_suggestion_8"))
    skillset_data.append(temp_data)
    return skillsets
