#!/usr/bin/env python3
import random, os, sys
import subprocess as sp
from ase import Atoms
from ase.io import read
from pymatgen import Structure, Element,Molecule
from pymatgen.io.ase import AseAtomsAdaptor
from ase.calculators.lammpsrun import write_lammps_data

def get_lammps_structures(filename,format,elements,index=":",sort_by_id=True,style="atomic"):
    '''
    parse pymatgen Structue obj. from lammps trajectory or dump file
    '''
    structures=[]
    if format=="lammps-data":
       atoms=read(filename,format='lammps-data',style=style,index=index,sort_by_id=sort_by_id)
    elif format=="lammps-dump":
       atoms=read(filename,format='lammps-dump',index=index)
    else:
       return structures   
    if isinstance(atoms,list):
       pass
    else:
       atoms=[atoms]
    elements_dict=dict(enumerate(elements,1))
    for atom in atoms:
       index=atom.get_atomic_numbers()
       new_index=[Element(elements_dict[i]).Z for i in index]
      # print(index)
      # print(new_index)
      # print(atom.positions)
       atom.set_atomic_numbers(new_index)
       unsorted_structure=AseAtomsAdaptor.get_structure(atom,cls=Structure)
       sorted_structure=sort_by_element(unsorted_structure,elements)
       structures.append(sorted_structure)
    return structures

def set_lammps_data(filename,structure,specorder,force_skew=True,prismobj=None,velocities=False):
    '''
    write lammps configure data
    '''
    assert isinstance(structure,Structure)
    atom=AseAtomsAdaptor.get_atoms(structure)
    write_lammps_data(filename,atom,specorder=specorder,force_skew=force_skew,prismobj=prismobj,velocities=velocities)

def sort_by_element(structure,std_elements_list):
    assert isinstance(structure,Structure)
    return structure.get_sorted_structure(key=lambda site: index_element(site.specie.name,std_elements_list))
    
def index_element(element,std_elements_list):
    return std_elements_list.index(element)

def get_elements_dict(elements):   
    elements_dict=dict(enumerate(elements,1))
    inv_elements_dict = dict(zip(elements_dict.values(), elements_dict.keys()))
    return elements_dict,inv_elements_dict

