import xml.etree.ElementTree as ET
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, DCTERMS
import datetime
import sys
import re
import urllib.parse

def xml_to_ttl(xml):
  try:
    tree = ET.fromstring(xml) 
    root = tree

    #ttlデータの作成
    data = Graph()

    pd3 = Namespace('http://DigitalTriplet.net/2021/08/ontology#')
    data.bind('pd3', pd3)
    data.bind('rdf', RDF)
    data.bind('dcterms', DCTERMS)
    data.bind('rdfs', RDFS)
    epURI_Num = 0

    for diagram in root.iter('diagram'):
      epstyle = ''
      if(diagram[0][0][0].get('style') != None):
        epstyle = diagram[0][0][0].get('style').split(';')

      for element in epstyle:
        if('URI=' in element):

          #タイムスタンプをuriに追加
          t_delta = datetime.timedelta(hours=9)
          JST = datetime.timezone(t_delta, 'JST')
          now = datetime.datetime.now(JST)
          d = '{:%Y%m%d%H%M%S}'.format(now) 

          epuri = element.replace('URI=','')
          if(epuri[-1] == '/'):
            epuri = epuri[:-1]
          epuri = epuri + '/' + d + '/'
          epURI = Namespace(epuri)
          ep = URIRef(epuri)
          data.add((ep, RDF.type, pd3.EngineeringProcess))
        elif('prefix=' in element):
          prefix = element.replace('prefix=','')
          data.bind(prefix, epURI)
        elif('title=' in element):
          title = element.replace('title=', '')
          data.add((ep, DCTERMS.title, Literal(title)))
        elif('creator=' in element):
          creator = element.replace('creator=', '')
          data.add((ep, DCTERMS.creator, Literal(creator)))
        elif('description=' in element):
          description = element.replace('description=', '')
          data.add((ep, DCTERMS.description, Literal(description)))
        elif('identifier=' in element):
          identifier = element.replace('identifier=', '')
          data.add((ep, DCTERMS.identifier, Literal(identifier)))
        elif('epType=' in element):
          eptype = element.replace('eptype', '')
          data.add((ep, pd3.epType, Literal(eptype)))

      epURI_Num += 1  

      #エンティティの情報を入手
      for mxCell in diagram.iter('mxCell'):
        style = mxCell.get('style')
        if(style != None):
          #action
          if('pd3type=action' in style):
            #★★★★★★★
            # 2022/1/12 mod Start Man
            id = mxCell.get('id').replace('_','-')
            # 2022/1/12 mod End Man
            action = URIRef(epuri + id)
            #idとvalueを取得
            value = mxCell.get('value')

            data.add((action, RDF.type, pd3.Action))
            data.add((action, pd3.id, Literal(id)))
            data.add((action, pd3.value, Literal(value)))

            #座標、形状を取得
            data.add((action, pd3.geoBoundingWidth, Literal(mxCell[0].get('width'))))
            data.add((action, pd3.geoBoundingHeight, Literal(mxCell[0].get('height'))))
            data.add((action, pd3.geoBoundingX, Literal(mxCell[0].get('x'))))
            data.add((action, pd3.geoBoundingY, Literal(mxCell[0].get('y'))))

            pd3actioncheck = True
            for element in style.split(';'):
              if('pd3layer=' in element):
                layer = Literal(element.replace('pd3layer=', ''))
                data.add((action, pd3.layer, layer))
              elif('pd3action=' in element):
                actionType = element.replace('pd3action=', '')
                if(actionType == 'ECDP'):
                  actionType = 'define problem'
                elif(actionType == 'ECCAI'):
                  actionType = 'collect/analyze information'
                elif(actionType == 'ECGH'):
                  actionType = 'generate hypothesis'
                elif(actionType == 'ECESI'):
                  actionType = 'evaluate/select information'
                elif(actionType == 'ECEX'):
                  actionType = 'execute'
                data.add((action, pd3.actionType, Literal(actionType)))
                pd3actioncheck = False
              elif('seeAlso=' in element):
                # 2022/1/17 mod Start Man
                seeEntities = element.replace('seeAlso=', '').split(',')
                for seeEntity in seeEntities:
                  #seeAlso uriを取得
                  seeTemp= seeEntity.replace('seeAlso=', '').split('[')
                  print(seeTemp)
                  if(seeTemp[0] != None) and (seeTemp[1] != None):
                    seeURI = Namespace(seeTemp[0])
                    #seeAlso prefixとidを取得
                    seeprefix = seeTemp[1].split(']')
                    if(seeprefix[0] != None) and (seeprefix[1] != None):
                      data.bind(seeprefix[0], seeURI)
                      data.add((action, RDFS.seeAlso, URIRef(seeURI + seeprefix[1])))
                """
                seeEntities = element.replace('seeAlso=', '').replace('['+prefix+']', '').split(',')
                for seeEntity in seeEntities:
                    data.add((action, RDFS.seeAlso, URIRef(epuri + seeEntity)))
                """
                # 2022/1/17 mod End Man
            if(pd3actioncheck):
              data.add((action,pd3.actionType, Literal('nil')))
            pd3actioncheck = True

            #attribution, container, input, outputを取得
            attribution_id = mxCell.get('parent')

            for mxCell1 in diagram.iter('mxCell'):
              if(mxCell1.get('target') == mxCell.get('id')):
                data.add((action, pd3.input, URIRef(epuri + mxCell1.get('id').replace('_','-'))))
                source_id = mxCell1.get('source')
                for mxCell2 in diagram.iter('mxCell'):
                  if((mxCell2.get('style') != None) & (mxCell2.get('id') == source_id)):
                    if('pd3type=container' in mxCell2.get('style')):
                      data.add((action, pd3.expansion, URIRef(epuri + mxCell2.get('id').replace('_','-'))))
                      break
              elif((mxCell1.get('id') == attribution_id) & (mxCell1.get('style') != None)):
                data.add((action, pd3.attribution, URIRef(epuri + attribution_id.replace('_','-'))))
              elif(mxCell1.get('source') == mxCell.get('id')):
                data.add((action, pd3.output, URIRef(epuri + mxCell1.get('id').replace('_','-'))))

          #container
          elif('pd3type=container' in style):
            container = URIRef(epuri + mxCell.get('id').replace('_','-'))
            #idを取得
            id = mxCell.get('id')
            data.add((container, RDF.type, pd3.Container))
            data.add((container, pd3.id, Literal(mxCell.get('id').replace('_','-'))))
            
            #座標、形状を取得
            data.add((container, pd3.geoBoundingWidth, Literal(mxCell[0].get('width'))))
            data.add((container, pd3.geoBoundingHeight, Literal(mxCell[0].get('height'))))
            data.add((container, pd3.geoBoundingX, Literal(mxCell[0].get('x'))))
            data.add((container, pd3.geoBoundingY, Literal(mxCell[0].get('y'))))

            #layer, containerTypeを取得
            for element in style.split(';'):
              if('pd3layer=' in element):
                layer = Literal(element.replace('pd3layer=', ''))
                data.add((container, pd3.layer, layer))
              elif('containertype=' in element):
                containertype = element.replace('containertype=', '')
                data.add((container, pd3.containerType, Literal(containertype)))
              elif('seeAlso=' in element):
                seeEntities = element.replace('seeAlso=', '').replace('['+prefix+']', '').split(',')
                for seeEntity in seeEntities:
                  data.add((action, RDFS.seeAlso, URIRef(epuri + seeEntity)))
                
            #valueを取得
            if(containertype == 'whilebox' or containertype == 'whilecontainer'):
              value = 'nil'
            else:
              value = mxCell.get('value')
            data.add((container, pd3.value, Literal(value)))

            #member, target, source, contractionを取得
            for mxCell1 in diagram.iter('mxCell'):
              if(mxCell1.get('parent') == id):
                member_id = mxCell1.get('id').replace('_','-')
                data.add((container, pd3.member, URIRef(epuri + member_id)))
              elif(mxCell1.get('source') == id):
                target_id = mxCell1.get('target')
                if target_id:
                  data.add((container, pd3.output, URIRef(epuri + target_id.replace('_','-'))))
                for mxCell2 in diagram.iter('mxCell'):
                  if((mxCell2.get('style') != None) & (mxCell2.get('id') == target_id)):
                    if('pd3type=action' in mxCell2.get('style')):
                      data.add((container, pd3.contraction, URIRef(epuri + mxCell2.get('id').replace('_','-'))))
                      break

          #arc
          elif('pd3type=arc' in style):
            if(mxCell.get('target') != None):
              arc = URIRef(epuri + mxCell.get('id').replace('_','-'))

              #id,valueを取得
              id = mxCell.get('id')
              value = mxCell.get('value')
              if(value == None or value == ''):
                value = ''
                for mxCell1 in diagram.iter('mxCell'):
                    if(mxCell1.get('style') != None):
                      if('edgeLabel' in mxCell1.get('style')):
                        if(id == mxCell1.get('parent')):
                          value = mxCell1.get('value')
                          break
              data.add((arc, pd3.id, Literal(mxCell.get('id').replace('_','-'))))
              data.add((arc, pd3.value, Literal(value)))

              #layerを取得
              for element in style.split(';'):
                if('pd3layer=' in element):
                  layer = element.replace('pd3layer=', '')
              data.add((arc, pd3.layer, Literal(layer)))

              #attributionを取得
              attribution_id = mxCell.get('parent')
              for mxCell1 in diagram.iter('mxCell'):
                if((mxCell1.get('id') == attribution_id) & (mxCell1.get('style') != None)):
                  data.add((arc, pd3.attribution, URIRef(epuri + attribution_id.replace('_','-'))))

              #sourceがあればFlowか, ContainerFlowか, ObjectをsourceとするSupFlow
              source = mxCell.get('source')
              target = mxCell.get('target')
              if(source != None):
                #source, targetを取得
                data.add((arc, pd3.source, URIRef(epuri + source.replace('_','-'))))
                data.add((arc, pd3.target, URIRef(epuri + target.replace('_','-'))))

                #exitX, exitY, entryX, entryYを取得            
                for element in style.split(';'):
                  if('exitX=' in element):
                    exitX = element.replace('exitX=', '')
                    data.add((arc, pd3.exitX, Literal(exitX)))
                  elif('exitY=' in element):
                    exitY = element.replace('exitY=', '')
                    data.add((arc, pd3.exitY, Literal(exitY)))
                  elif('entryX=' in element):
                    entryX = element.replace('entryX=', '')
                    data.add((arc, pd3.entryX, Literal(entryX)))
                  elif('entryY=' in element):
                    entryY = element.replace('entryY=', '')
                    data.add((arc, pd3.entryY, Literal(entryY)))
                  elif('seeAlso=' in element):
                    seeEntities = element.replace('seeAlso=', '').replace('['+prefix+']', '').split(',')
                    for seeEntity in seeEntities:
                        data.add((action, RDFS.seeAlso, URIRef(epuri + seeEntity)))
                      
                for mxCell1 in diagram.iter('mxCell'):
                  if(mxCell1.get('id') == source):
                    #Flow
                    if(mxCell1.get('style') != None):
                      if('pd3type=action' in mxCell1.get('style')):
                          data.add((arc, RDF.type, pd3.Flow))
                          data.add((arc, pd3.arcType, Literal('information')))
                          break

                        #ContainerFlow
                      elif('pd3type=container' in mxCell1.get('style')):
                        data.add((arc, RDF.type, pd3.ContainerFlow))
                        data.add((arc, pd3.arcType, Literal('hierarchization')))
                        break
                      #tool/knowledgeのSupFlow
                      elif('pd3type=object' in mxCell1.get('style')):
                        data.add((arc, RDF.type, pd3.SupFlow))
                        data.add((arc, pd3.arcType, Literal('tool/knowledge')))
                        break

              else:
                #sourceがなければSupFlow
                data.add((arc, RDF.type, pd3.SupFlow))

                #targetの取得
                data.add((arc, pd3.target, URIRef(epuri + target.replace('_','-'))))

                #entryX,entryYの取得
                for element in style.split(';'):
                  if('entryX=' in element):
                    entryX = element.replace('entryX=', '')
                    data.add((arc, pd3.entryX, Literal(entryX)))
                  elif('entryY=' in element):
                    entryY = element.replace('entryY=', '')
                    data.add((arc, pd3.entryY, Literal(entryY)))
                  elif('seeAlso=' in element):
                    seeEntities = element.replace('seeAlso=', '').replace('['+prefix+']', '').split(',')
                    for seeEntity in seeEntities:
                        data.add((action, RDFS.seeAlso, URIRef(epuri + seeEntity)))
                        
                #arcTypeの取得
                if("entryY=1;" in style):
                  data.add((arc, pd3.arcType, Literal('tool/knowledge')))
                elif("entryY=0.5;" in style):
                  data.add((arc, pd3.arcType, Literal('rationale')))
                elif("entryY=0;" in style):
                  if("entryX=0.5;" in style):
                    data.add((arc, pd3.arcType, Literal('intention')))
                  elif("entryX=1;" in style):
                    data.add((arc, pd3.arcType, Literal('annotation')))

                #位置を取得
                for mxPoint in mxCell.iter('mxPoint'):
                  if(mxPoint.get('as') == 'sourcePoint'):
                    data.add((arc, pd3.geoSourcePointX, Literal(mxPoint.get('x'))))
                    data.add((arc, pd3.geoSourcePointY, Literal(mxPoint.get('y'))))
                  elif(mxPoint.get('as') == 'targetPoint'):
                    data.add((arc, pd3.geoTargetPointX, Literal(mxPoint.get('x'))))
                    data.add((arc, pd3.geoTargetPointY, Literal(mxPoint.get('y'))))
          # 2022/1/11 add Start Man
          #object
          elif('pd3type=object' in style):
            object = URIRef(epuri + mxCell.get('id').replace('_','-'))
            #idとvalueを取得
            id = mxCell.get('id').replace('_','-')
            value = mxCell.get('value')

            data.add((object, RDF.type, pd3.Object))
            data.add((object, pd3.id, Literal(id)))
            data.add((object, pd3.value, Literal(value)))

            #座標、形状を取得
            data.add((object, pd3.geoBoundingWidth, Literal(mxCell[0].get('width'))))
            data.add((object, pd3.geoBoundingHeight, Literal(mxCell[0].get('height'))))
            data.add((object, pd3.geoBoundingX, Literal(mxCell[0].get('x'))))
            data.add((object, pd3.geoBoundingY, Literal(mxCell[0].get('y'))))

            #layerを取得
            for element in style.split(';'):
              if('pd3layer=' in element):
                layer = element.replace('pd3layer=', '')
            data.add((object, pd3.layer, Literal(layer)))

            #outputを取得
            for mxCell1 in diagram.iter('mxCell'):
              if(mxCell1.get('source') == mxCell.get('id')):
                data.add((object, pd3.output, URIRef(epuri + (mxCell1.get('id').replace('_','-')))))

            #attributionを取得
            attribution_id = mxCell.get('parent')
            for mxCell1 in diagram.iter('mxCell'):
              if((mxCell1.get('id') == attribution_id) & (mxCell1.get('style') != None)):
                data.add((object, pd3.attribution, URIRef(epuri + attribution_id.replace('_','-'))))       
          # 2022/1/11 add End Man

      for UserObject in diagram.iter('UserObject'):
        id = UserObject.get('id')
        value = UserObject.get('label')
        object = URIRef(epuri + id)

        #idとvalueの取得
        data.add((object, RDF.type, pd3.Object))
        data.add((object, pd3.id, Literal(id)))
        data.add((object, pd3.value, Literal(value)))

        #外部参照のurlの取得
        # seeAlso_url = UserObject.get('link')
        # print(seeAlso_url)
        # data.add((object, RDFS.seeAlso, seeAlso_url))

        #レイヤーの取得
        style = UserObject[0].get('style').split(';')
        for element in style:
          if('pd3layer=' in element):
            layer = element.replace('pd3layer=', '')
            data.add((object, pd3.layer, Literal(layer)))

        #座標、形状を取得
        data.add((object, pd3.geoBoundingWidth, Literal(UserObject[0][0].get('width'))))
        data.add((object, pd3.geoBoundingHeight, Literal(UserObject[0][0].get('height'))))
        data.add((object, pd3.geoBoundingX, Literal(UserObject[0][0].get('x'))))
        data.add((object, pd3.geoBoundingY, Literal(UserObject[0][0].get('y'))))

    return data.serialize()
  except Exception as e:
    print(e)
    return

if __name__=="__main__":
  # xml_to_ttl(args.file)
  data = urllib.parse.unquote(sys.stdin.read())
  data = re.sub('\++',' ', data)
  print('Content-type: text/html')
  print("\n\n")
  xml_to_ttl(data)
  print("\n")