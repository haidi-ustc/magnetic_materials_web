#coding=utf-8
import os
import time
import json
import pprint
import base64
from flask import render_template, make_response, request, abort, Flask, jsonify, send_from_directory
from flask_restful import Api, Resource, reqparse
from flask_rest_service import app, api, mongo, cache, ALLOWED_EXTENSIONS, basedir
from werkzeug.utils import secure_filename

from io import StringIO
#from werkzeug.contrib.cache import GAEMemcachedCache

#from flask_cache import Cache
#cache = Cache()

from bson.objectid import ObjectId

from pymatgen import MPRester,Composition,Structure
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.entries.compatibility import MaterialsProjectCompatibility
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.analysis.phase_diagram import *

from flask_rest_service.lammps import  set_lammps_data

MAPI_KEY='QFrf8k3D4yalbmAK'

mpr=MPRester(MAPI_KEY)
#cache = GAEMemcachedCache()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS

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

def save_file(entry_id,fmt='vasp'):
    #assert isinstance(struct,Structure)
    file_dir=os.path.join(basedir,app.config['DATA_FOLDER'])
    check_folder(file_dir)
    file_name=os.path.join(file_dir,entry_id+'.'+fmt) 
    if not os.path.isfile(file_name):
       struct=get_structure(entry_id)
       if fmt=='vasp':
          struct.to('poscar',file_name)
       elif fmt=='lammps':
          set_lammps_data(file_name,struct,struct.symbol_set)
       else:
          struct.to(fmt,file_name)


def get_structure(mm_id):
    ret=mongo.db.data.find_one({'entry_id':mm_id},{'structure':1})
    return Structure.from_dict(ret['structure'])

def check_folder(dir):   
    if not os.path.exists(dir):
        os.makedirs(dir)
     
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

def get_entry(mm_id):
    return mongo.db.data.find_one({'entry_id':mm_id})

def get_entries(mm_ids):
    return [get_entry(mm_id) for mm_id in mmids]

def thumbnails_information(max_entries=None,filter={}):

    fmt="%.3f"
    data=[]
    if max_entries is None:
       entries= mongo.db.data.find(filter)
    else:    
       total_count = mongo.db.data.find({},{}).count()
       number = min(max_entries, total_count)
       entries=  mongo.db.data.find(filter)[0:number]

    for entry in entries:
       # print(entry.keys())  
        thumb_dict={}
        st=Structure.from_dict(entry['structure'])
        comp = st.composition
        thumb_dict['mmid']=entry['entry_id']
        thumb_dict['formula']=html_formula(st.formula.replace(' ',''))
        #print(html_formula(st.formula.replace(' ','')))
        thumb_dict['spacegroup']=entry['data']['spacegroup']['symbol']
        mpara={'potcar_symbols': entry['parameters']['potcar_symbols']}
        energy=entry['energy']/st.num_sites
        #ef,stability_info=get_stability(comp,energy,mpara)
        #thumb_dict['formation_energy']=fmt%(ef)
        #thumb_dict['e_above_hull']=fmt%(stability_info['e_above_hull'])
        gap=entry['data']['bandgap']
        thumb_dict['bandgap']=fmt%(gap) if gap else gap 
        thumb_dict['volume']=fmt%(st.volume)
        thumb_dict['density']=fmt%(st.density)
        thumb_dict['nsites']=st.num_sites
        data.append(thumb_dict)
    return data            

@app.route('/query', methods=['GET'])
def query():
    message=None
    in_string = request.args.get("in_string")
    sel_type = request.args.get("select_type")
    assert sel_type in ["formula",'groupid','element','materialid']
    if sel_type=="formula":
       try:
          comp=Composition(in_string.strip())
          filter={'composition':dict(comp.as_dict())}
          #print(filter)
          #entries= mongo.db.data.find_one(filter)
          #print(entries)
       except Exception as ex:
          message = str(ex)
       
    elif sel_type=="element":
       try:
          elements=[Element(i) for i  in in_string.strip().split()]
          filter={}
          for element in elements:
              filter["composition."+element.symbol]={'$gt':0}
          #print(filter)
          #entries= mongo.db.data.find_one(filter)
          #print(entries)
          #cond="{'composition.Fe':{'$gt':0},'composition.Co':{'$gt':0},'composition.N':{'$gt':0}})"
       except Exception as ex:
          message = str(ex)
    elif sel_type=='groupid':
       try:
          groupid=int(in_string)
          filter={'data.spacegroup.number':groupid}
       except Exception as ex:
          message = str(ex)
    else:
       try:
          entry_id=in_string
          filter={'entry_id':entry_id}
       except Exception as ex:
          message = str(ex)
 
    if message is None:
       thumb_data=thumbnails_information(filter=filter)
    else:
       thumb_data={}  

    return make_response(render_template('index.html',message=message,data=thumb_data))

@app.route('/about')
def about():
    return make_response(render_template('about.html'))

@app.route('/info/<mm_id>')
def show_info(mm_id):
    fmt="%.3f"
    lfmt="%12.8f"
    material_details={}
    space_group={}
    lattice={}
    structure={}
    entry=get_entry(mm_id) 
    st=Structure.from_dict(entry['structure'])
    comp = st.composition
    st_formula=html_formula(st.formula.replace(' ',''))
    space_group=entry['data']['spacegroup']

    mpara={'potcar_symbols': entry['parameters']['potcar_symbols']}
    energy=entry['energy']/st.num_sites
    #ef,stability_info=get_stability(comp,energy,mpara)

    material_details['mag_mom']=fmt%(entry['data']['magmoment'])
    try:
      material_details['order']=entry['data']['magorder']
    except:
      material_details['order']=None

    material_details['MAE']=fmt%(entry['data']['MAE'])
    try:
       material_details['curie_T']=fmt%(entry['data']['curie_T'])
    except:
      material_details['curie_T']=None
    
    try:
       material_details['bandgap']=fmt%(entry['data']['bandgap'])
    except:
       material_details['bandgap']=None

    #material_details['f_e']=fmt%(ef)
    #material_details['e_hull']=fmt%(stability_info['e_above_hull'])
    material_details['density']=fmt%(st.density)
    #if stability_info['e_above_hull'] > 1e-3:
    #   ret=stability_info
    #   formula=[d['formula'] for d in ret['decomposes_to']]
    #   material_details['decompose']=' + '.join([html_formula(i) for i in formula])
    #else:   
    #   material_details['decompose']='stable'
   
    lattice['a']=lfmt%st.lattice.a 
    lattice['b']=lfmt%st.lattice.b 
    lattice['c']=lfmt%st.lattice.c
    lattice['alpha']=fmt%st.lattice.alpha
    lattice['beta']=fmt%st.lattice.beta
    lattice['gamma']=fmt%st.lattice.gamma
    lattice['volume']=st.volume


    structure=[] 
    for i,site in enumerate(st):
        atom={}
        atom['index']=i+1
        atom['specie']=site.specie.value
        atom['x']=lfmt%site.frac_coords[0]
        atom['y']=lfmt%site.frac_coords[1]
        atom['z']=lfmt%site.frac_coords[2]
        structure.append(atom)

    #out=str(pprint.pformat(entry, indent=4))
    #print(entry)
    #return out
    return make_response(render_template('info.html',
                            mm_id=mm_id,
                            formula=st_formula,
                            mat_detail=material_details,
                            spg=space_group,
                            lat=lattice,
                            struct=structure
               ))

@app.route('/download',methods=['GET'])
def download():
    thumb_data=thumbnails_information()
    ret=str(pprint.pformat(thumb_data, indent=4))
    return ret

@app.route('/',methods=['GET'])
@cache.cached(timeout=300,key_prefix='index')
def index():
    #author_info={"Author":"haidi"}
    thumb_data=thumbnails_information(max_entries=20)
    
    return make_response(render_template('index.html',data=thumb_data))

@app.route('/test/upload')
def upload_test():
    return render_template('upload.html')
 
# upload file
@app.route('/api/upload',methods=['POST'],strict_slashes=False)
def api_upload():
    file_dir=os.path.join(basedir,app.config['UPLOAD_FOLDER'])
    check_folder(file_dir)
    f=request.files['myfile']  # 从表单的file字段获取文件，myfile为该表单的name值
    print(f)
    if f and allowed_file(f.filename):  # 判断是否是允许上传的文件类型
        fname=secure_filename(f.filename)
        #print(fname)
        ext = fname.rsplit('.',1)[1]  # 获取文件后缀
        unix_time = int(time.time())
        new_filename=str(unix_time)+'.'+ext  # 修改了上传的文件名
        f.save(os.path.join(file_dir,new_filename))  #保存文件到upload目录
        #token = base64.b64encode(new_filename)
        #print(new_filename)
 
        return jsonify({"errno":0,"errmsg":"success","token":new_filename})
    else:
        return jsonify({"errno":1001,"errmsg":"failed"})

@app.route('/download/<mm_id>/<fmt>')
def download_file(mm_id,fmt):
    #print(mm_id)
    #print(file_name)
    file_name=mm_id+'.'+fmt
    save_file(mm_id,fmt)  
    file_dir=os.path.join(basedir,app.config['DATA_FOLDER'])
    if os.path.isfile(os.path.join(file_dir,file_name)):
       return send_from_directory(file_dir, file_name, as_attachment=True)
    abort(404)

@app.route("/downloads/<file_name>", methods=['GET','POST']) 
def fdownload(file_name):
    #if request.method=="GET" or "POST":
    file_dir=os.path.join(basedir,app.config['UPLOAD_FOLDER'])
    if os.path.isfile(os.path.join(file_dir,file_name)):
       response = make_response(send_from_directory(file_dir, file_name, as_attachment=True))
       response.headers["Content-Disposition"] = "attachment; filename={}".format(file_name.encode().decode('utf-8'))
       return response
    abort(404)

