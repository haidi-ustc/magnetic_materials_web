import json
import pprint
from flask import render_template, make_response, request, abort, Flask
from flask_restful import Api, Resource, reqparse
from flask_rest_service import app, api, mongo
from bson.objectid import ObjectId

from pymatgen import MPRester,Composition,Structure
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.entries.compatibility import MaterialsProjectCompatibility
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.analysis.phase_diagram import *
MAPI_KEY='QFrf8k3D4yalbmAK'

mpr=MPRester(MAPI_KEY)

def get_stability(comp,energy,mpara):
    compat=MaterialsProjectCompatibility()
    print(mpara)
    #mycomp=Composition("Co10Fe2N4")
    mycomp=Composition(comp)
    unprocessed_entries=mpr.get_entries_in_chemsys([e.symbol for e in mycomp.elements])
    print("len unprocessed entries: %d"%(len(unprocessed_entries)))
    #my_eng_per_atom=-7.47035
    my_eng_per_atom=energy
    #mpara={'potcar_symbols':['pbe Fe_pv','pbe Co_pv','pbe N'],'hubbards':{'Fe':5.3}}
    #mpara={'potcar_symbols':['pbe Fe_pv','pbe Co','pbe N']}
    processed_entries=compat.process_entries(unprocessed_entries)
    print("len processed entries: %d"%(len(processed_entries)))
    my_en=ComputedEntry(mycomp,my_eng_per_atom*mycomp.num_atoms,parameters=mpara)
    corrections_dict=compat.get_corrections_dict(my_en)
    pretty_corr=["{}:{}".format(k,round(v,3)) for k,v in corrections_dict.items()]
    print('pretty_corr')
    print(pretty_corr)
    my_en.correction=sum(corrections_dict.values())
    processed_entries.append(my_en)
    pd=PhaseDiagram(processed_entries)
    print("formation energy %f "%pd.get_form_energy(my_en))
    #print("len stable phases: %" %)
    #print(pd.stable_entries)
    #print("e above the hull %f"%pd.get_e_above_hull(my_en))
    #print("decompose to: ")
    #decomp=[]
    #for comp  in pd.get_decomp_and_e_above_hull(my_en)[0]:
    #    decomp.append(comp.composition.formula.replace(' ',''))
    #print(decomp)
    return pd.get_form_energy(my_en),mpr.get_stability([my_en])[0]


def html_formula(f):
    return re.sub(r"([\d.]+)", r"<sub>\1</sub>", f)

def calculate_stability(entry):
    functional = d["pseudo_potential"]["functional"]
    syms = ["{} {}".format(functional, l)
            for l in d["pseudo_potential"]["labels"]]
    entry = ComputedEntry(Composition(d["unit_cell_formula"]),
                          d["output"]["final_energy"],
                          parameters={"hubbards": d["hubbards"],
                                      "potcar_symbols": syms})
    data = m.get_stability([entry])[0]
    for k in ("e_above_hull", "decomposes_to"):
        d["analysis"][k] = data[k]

def find_entry(mm_id):
    return mongo.db.data.find_one({'entry_id':mm_id})

def thumbnails_information():
    fmt="%.3f"
    data=[]
    for entry in mongo.db.data.find():
       # print(entry.keys())  
        thumb_dict={}
        st=Structure.from_dict(entry['structure'])
        comp = st.composition
        thumb_dict['mmid']=entry['entry_id']
        thumb_dict['formula']=html_formula(st.formula.replace(' ',''))
        print(html_formula(st.formula.replace(' ','')))
        thumb_dict['spacegroup']=entry['data']['spacegroup']['symbol']
        mpara={'potcar_symbols': entry['parameters']['potcar_symbols']}
        energy=entry['energy']/st.num_sites
        ef,stability_info=get_stability(comp,energy,mpara)
        thumb_dict['formation_energy']=fmt%(ef)
        thumb_dict['e_above_hull']=fmt%(stability_info['e_above_hull'])
        gap=entry['data']['bandgap']
        thumb_dict['bandgap']=fmt%(gap) if gap else gap 
        thumb_dict['volume']=fmt%(st.volume)
        thumb_dict['density']=fmt%(st.density)
        thumb_dict['nsites']=st.num_sites
        data.append(thumb_dict)
    return data            
        #el_amt = st.composition.get_el_amt_dict()
        #d.update({"unit_cell_formula": comp.as_dict(),
        #          "reduced_cell_formula": comp.to_reduced_dict,
        #          "elements": list(el_amt.keys()),
        #          "nelements": len(el_amt),
        #          "pretty_formula": comp.reduced_formula,
        #          "anonymous_formula": comp.anonymized_formula,
        #          "nsites": comp.num_atoms,
        #          "chemsys": "-".join(sorted(el_amt.keys()))})
        #st.formula
        #st.density
        #st.volume

@app.route('/info/<mm_id>')
def show_info(mm_id):
    entry=find_entry(mm_id) 
    out=str(pprint.pformat(entry, indent=4))
    #print(entry)
    return out

@app.route('/',methods=['GET'])
def index():
    #author_info={"Author":"haidi"}
    thumb_data=thumbnails_information()
    
    return make_response(render_template('index.html',data=thumb_data))

#api.add_resource(Root, '/')
#api.add_resource(ReadingList, '/items/')
#api.add_resource(Reading, '/items/<ObjectId:reading_id>')
